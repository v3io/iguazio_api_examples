class ExceptionWithResponse(IOError):

    def __init__(self, status_code, body=None, content_type=None):
        self._status_code = status_code
        self._body = body
        self._content_type = content_type

    @property
    def body(self):
        return self._body

    @property
    def status_code(self):
        return self._status_code

    @property
    def content_type(self):
        return self._content_type
