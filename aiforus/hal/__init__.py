"""Hardware abstraction layer.

The assistant only talks to these small interfaces. Today they are backed by
a laptop webcam, microphone and speakers; a smart-glasses adapter later only
needs to implement the same methods.

Heavy third-party libraries are imported lazily inside each adapter, so the
core (and the test-suite) runs without OpenCV, PyAudio or pyttsx3 installed.
"""


class ComponentUnavailable(RuntimeError):
    """An optional component can't be used (library missing, no device...)."""
