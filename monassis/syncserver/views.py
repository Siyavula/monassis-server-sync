from __future__ import division

from pyramid.view import view_config
from pyramid.httpexceptions import HTTPFound, HTTPNotFound, HTTPBadRequest, HTTPForbidden

import sqlalchemy
import logging

def tic():
    import time
    return time.time()

def toc(startTime, extraInfo=None):
    import time
    stopTime = time.time()
    import inspect
    log = logging.getLogger('tictoc')
    message = "%s took %.3es"%(inspect.stack()[1][3], stopTime-startTime)
    if extraInfo is not None:
        message += " [%s]"%extraInfo
    log.info(message)


@view_config(context=HTTPNotFound, renderer='templates/404.pt')
def not_found(self, request):
    try:
        userId, userSession = get_user_info(request)
        message = '''Got a 404 at URL %s
session: %s'''%(request.url, repr(userSession))
    except HTTPForbidden, e:
        message = 'Got an anonymous 404 at URL %s'%(request.url)

    log = logging.getLogger(__name__)
    log.warning(message)

    request.response.status_int = 404
    return {}


@view_config(route_name='entry_root', renderer='json')
def entry_root_view(request):
    tictoc = tic()
    from monassis.qnxmlservice import dbmodel
    database = dbmodel.db
    table = dbmodel.tables['templates']
    idColumn = table.c.id
    hashColumns = [table.c.zipdata, table.c.muesli]
    select = sqlalchemy.sql.select([
        idColumn,
        sqlalchemy.func.md5(
            sqlalchemy.func.concat(*(
                [sqlalchemy.sql.cast(column, sqlalchemy.Text()) + "," for column in hashColumns])))])
    result = database.execute(select)
    row = result.fetchone()
    response = {
        'id': row[0],
        'hash': row[1],
    }
    toc(tictoc)
    return response
