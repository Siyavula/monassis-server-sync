from pyramid.paster import get_appsettings

from syncserver.models.support import DBSession
from syncserver.models import Base
from syncserver import main
from webtest import TestApp


def init_testing_app():
    app = main({}, **get_appsettings('test.ini#main'))
    return TestApp(app)


def init_testing_db():
    # NOTE: init_testing_app must have been called first

    # Load sync server database
    Base.metadata.create_all()
    return DBSession()
