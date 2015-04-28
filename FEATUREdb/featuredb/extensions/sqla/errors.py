try:
    from flask import abort
except ImportError:
    import warnings
    warnings.warn("Flask-SQLAlchemy not present! Using standard SQLAlchemy base classes")

    class MockHTTPError(RuntimeError):
        def __init__(self, code):
            super(MockHTTPError, self).__init__("Program aborted with error code {:d}".format(code))
            self.code = code

    def abort(code):
        raise MockHTTPError("Program aborted with num {:d}".format(code))

def abort_not_found():
    abort(404)

def abort_not_authorized():
    abort(403)
