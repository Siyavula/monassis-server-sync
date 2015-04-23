import transaction

from pyramid.paster import get_appsettings

import syncserver.requests
from syncserver.models.support import DBSession
from syncserver.models import Base, Lock, LockError

def init_testing_app():
    from syncserver import main
    from webtest import TestApp

    app = main({}, **get_appsettings('test.ini#main'))
    return TestApp(app)


def init_testing_db():
    # NOTE: init_testing_app must have been called first

    # Load records database
    from syncserver.tests import dbmodel

    # Load sync server database
    Base.metadata.create_all()
    return DBSession()
