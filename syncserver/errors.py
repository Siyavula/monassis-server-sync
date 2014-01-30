import json

from pyramid.httpexceptions import HTTPBadRequest, HTTPLocked
from pyramid.threadlocal import get_current_request


class SyncServerError(object):
    """
    Mixin class to support sending syncserver errors over HTTP.
    """

    def __init__(self, message, **kwargs):
        super(SyncServerError, self).__init__(self, **kwargs)

        self._error_code = None
        self.body = json.dumps(self.make_error(message))
        self.headers['Content-Type'] = 'application/json'

    def get_error_code(self):
        if self._error_code is None:
            return self.__class__.__name__
        return self._error_code

    def set_error_code(self, value):
        self._error_code = value

    error_code = property(get_error_code, set_error_code)

    def make_error(self, message):
        return {
            'request_id': get_current_request().request_id,
            'error': {
                'status': self.status_code,
                'code': self.error_code,
                'message': message,
            }}


class DatabaseLocked(SyncServerError, HTTPLocked):
    pass
