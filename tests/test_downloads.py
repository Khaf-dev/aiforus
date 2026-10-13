import pytest

from aiforus.downloads import download_file


class FakeResponse:
    def __init__(self, payload, status=200):
        self.payload, self.status_code = payload, status

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")

    def iter_content(self, chunk_size):
        yield self.payload[:3]
        yield self.payload[3:]


class FakeSession:
    def __init__(self, status=200):
        self.calls = []
        self.status = status

    def get(self, url, stream, timeout):
        self.calls.append((url, stream, timeout))
        return FakeResponse(b"model-bytes", self.status)


def test_downloads_atomically_and_skips_existing(tmp_path):
    session = FakeSession()
    dest = tmp_path / "models" / "x.onnx"
    messages = []
    assert (
        download_file("https://h/x.onnx", dest, session=session, timeout_s=9, progress=messages.append)
        == dest
    )
    assert dest.read_bytes() == b"model-bytes"
    assert session.calls == [("https://h/x.onnx", True, 9)]
    assert messages == ["downloading https://h/x.onnx"]
    assert not list(dest.parent.glob("*.part"))
    download_file("https://h/x.onnx", dest, session=session)
    assert len(session.calls) == 1


def test_http_error_leaves_no_file(tmp_path):
    dest = tmp_path / "x.onnx"
    with pytest.raises(RuntimeError):
        download_file("https://h/x.onnx", dest, session=FakeSession(status=404))
    assert not dest.exists()
