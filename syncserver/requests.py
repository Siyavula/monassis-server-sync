from pyramid.events import NewRequest, NewResponse, BeforeRender
from pyramid.events import subscriber
from pyramid.threadlocal import get_current_request
import logging
log = logging.getLogger(__name__)

import uuid

from json import dumps

from syncserver.utils import now_utc 

@subscriber(NewRequest)
def add_request_id(event):
    """ Add a request id to all requests.  """
    event.request.request_id = str(uuid.uuid4())

@subscriber(NewResponse)
def response_request_id(event):
    """ Add request id to response. """
    event.response.headers['X-Request-Id'] = event.request.request_id


@subscriber(BeforeRender)
def render_request_id(event):
    """ Add request id to JSON responses. """
    if isinstance(event.rendering_val, dict):
        event.rendering_val['request_id'] = get_current_request().request_id
    

class RequestIdFilter(logging.Filter):
    """
    This filter adds a requestid parameter to the logging context.
    """
    def filter(self, record):
        # default
        record.requestid = '-'

        req = get_current_request()
        if req and hasattr(req, 'request_id'):
            record.requestid = req.request_id

        return record

def log_request(message, **kwargs):
    """
    Write a detailed request description to the log, useful
    for tracking detailed information about a request.

    Additional keyword arguments are serialised along with
    other request information and should be JSON compatible.

    The message is logged such that everything after a lozenge (<>)
    is JSON.
    """
    request = get_current_request()

    info = {
        "request_id": request.request_id,
        "remote_addr": request.remote_addr,
        "forwarded_for": request.headers.get('x-forwarded-for'),
        "ts": now_utc().isoformat(),
        }
    info.update(kwargs)

    log.info("REQUEST %s <> %s" % (message, dumps(info)))
