"""SQLite persistence: user preferences and enrolled faces.

Face encodings are stored as raw little-endian float64 bytes — never pickled.
The old ``database/face_encodings.pkl`` could execute arbitrary code if the
file was replaced; ``numpy.frombuffer`` can't.

Note: the database is not encrypted. Face encodings are biometric data, so
keep ``data/`` private. Encryption at rest is on the roadmap.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
from sqlalchemy import JSON, DateTime, ForeignKey, Integer, LargeBinary, String, create_engine, func, select
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, sessionmaker

_VECTOR_DTYPE = np.dtype("<f8")


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class Preference(Base):
    __tablename__ = "preferences"

    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    value: Mapped[Any] = mapped_column(JSON)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)


class Person(Base):
    __tablename__ = "persons"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    # Case-insensitive identity: "budi" and "Budi" are the same person.
    name_key: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    samples: Mapped[list[FaceSample]] = relationship(
        back_populates="person", cascade="all, delete-orphan", order_by="FaceSample.id"
    )


class FaceSample(Base):
    __tablename__ = "face_samples"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    person_id: Mapped[int] = mapped_column(ForeignKey("persons.id", ondelete="CASCADE"), index=True)
    vector: Mapped[bytes] = mapped_column(LargeBinary)
    dim: Mapped[int] = mapped_column(Integer)
    model: Mapped[str] = mapped_column(String(50))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    person: Mapped[Person] = relationship(back_populates="samples")


class Database:
    def __init__(self, path: str | Path) -> None:
        if str(path) == ":memory:":
            url = "sqlite://"
        else:
            path = Path(path)
            path.parent.mkdir(parents=True, exist_ok=True)
            url = f"sqlite:///{path}"
        self.engine = create_engine(url)
        Base.metadata.create_all(self.engine)
        self.session = sessionmaker(self.engine, expire_on_commit=False)

    def close(self) -> None:
        self.engine.dispose()


class PreferenceStore:
    def __init__(self, db: Database) -> None:
        self._db = db

    def get(self, key: str, default: Any = None) -> Any:
        with self._db.session() as session:
            pref = session.get(Preference, key)
            return default if pref is None else pref.value

    def set(self, key: str, value: Any) -> None:
        with self._db.session.begin() as session:
            pref = session.get(Preference, key)
            if pref is None:
                session.add(Preference(key=key, value=value))
            else:
                pref.value = value


def _key(name: str) -> str:
    return " ".join(name.split()).casefold()


class SqlFaceStore:
    """Face samples per person, keyed case-insensitively by name."""

    def __init__(self, db: Database, model: str = "dlib-128") -> None:
        self._db = db
        self._model = model

    def add(self, name: str, vector: np.ndarray) -> int:
        """Store one sample; return how many samples the person now has."""
        vec = np.asarray(vector, dtype=_VECTOR_DTYPE)
        if vec.ndim != 1 or vec.size == 0:
            raise ValueError("face encoding must be a non-empty 1-D vector")
        with self._db.session.begin() as session:
            person = session.scalar(select(Person).where(Person.name_key == _key(name)))
            if person is None:
                person = Person(name=name, name_key=_key(name))
                session.add(person)
            person.samples.append(FaceSample(vector=vec.tobytes(), dim=vec.size, model=self._model))
            session.flush()
            return len(person.samples)

    def count(self, name: str) -> int:
        with self._db.session() as session:
            stmt = select(func.count(FaceSample.id)).join(Person).where(Person.name_key == _key(name))
            return int(session.scalar(stmt) or 0)

    def all(self) -> dict[str, list[np.ndarray]]:
        result: dict[str, list[np.ndarray]] = {}
        with self._db.session() as session:
            rows = session.execute(
                select(Person.name, FaceSample.vector).join(FaceSample).where(FaceSample.model == self._model)
            )
            for name, blob in rows:
                result.setdefault(name, []).append(np.frombuffer(blob, dtype=_VECTOR_DTYPE))
        return result

    def names(self) -> list[str]:
        with self._db.session() as session:
            return list(session.scalars(select(Person.name).order_by(Person.name)))

    def remove(self, name: str) -> bool:
        with self._db.session.begin() as session:
            person = session.scalar(select(Person).where(Person.name_key == _key(name)))
            if person is None:
                return False
            session.delete(person)
            return True
