import logging


def main(global_config, **settings):
    """
    This function returns a Pyramid WSGI application.
    """
    # This must be done before new relic
    setup_logging()

    # This should be done before any pyramid imports if possible, certainly before make_wsgi_app()
    setup_newrelic(settings)
    setup_database(settings)

    from pyramid.config import Configurator
    config = Configurator(settings=settings)
    config.include('pyramid_tm')
    config.include('siyavula.models')

    setup_routes(config)

    config.scan()
    return config.make_wsgi_app()


def setup_routes(config):
    config.add_route('lock', '/{name}/lock', request_method='PUT')
    config.add_route('unlock', '/{name}/unlock', request_method='PUT')
    config.add_route('get_hash_hash', '/{name}/hash-hash', request_method='GET')
    config.add_route('get_hash_actions', '/{name}/hash-actions', request_method='GET')
    config.add_route('get_record', '/{name}/{section}/{id}/record', request_method='GET')
    config.add_route('get_records_for_section', '/{name}/{section}/records', request_method='GET')
    config.add_route('put_record', '/{name}/{section}/{id}/record', request_method='PUT')
    config.add_route('delete_record', '/{name}/{section}/{id}/record', request_method='DELETE')
    config.add_route('put_records_for_section', '/{name}/{section}/records', request_method='PUT')
    config.add_route('get_hash', '/{name}/{section}/{id}/hash', request_method='GET')
    config.add_route('put_hash', '/{name}/{section}/{id}/hash', request_method='PUT')
    config.add_route('delete_hash', '/{name}/{section}/{id}/hash', request_method='DELETE')
    config.add_route('put_hashes_for_section', '/{name}/{section}/hashes', request_method='PUT')
    config.add_route(
        'get_record_and_hash', '/{name}/{section}/{id}/record-hash', request_method='GET')
    config.add_route(
        'put_record_and_hash', '/{name}/{section}/{id}/record-hash', request_method='PUT')
    config.add_route(
        'delete_record_and_hash', '/{name}/{section}/{id}/record-hash', request_method='DELETE')
    config.add_route(
        'put_records_and_hashes_for_section', '/{name}/{section}/record-hashes',
        request_method='PUT')
    config.add_route('server_status', '/server_status', request_method='GET')


def setup_database(settings):
    # Don't know if this is necessary. When app is running stably on Northern Academy, see if
    # deleting this stops it from working.
    from sqlalchemy import engine_from_config
    from syncserver.models import DBSession, Base

    engine = engine_from_config(settings, 'sqlalchemy.')
    DBSession.configure(bind=engine)
    Base.metadata.bind = engine


def setup_logging():
    """
    Attach the request-id aware filter to the first handler in the chain. This isn't ideal, but the
    logging config doesn't give us an easy way to attach filters to via a config file.
    """
    handler = logging.getLogger().handlers[0]

    # the nose test handlers mess with this
    if not handler.__module__.startswith('nose'):
        import syncserver.requests
        handler.addFilter(syncserver.requests.RequestIdFilter())
        # force the formatter to use a request id
        if handler.formatter:
            setattr(
                handler.formatter, '_fmt', (
                    '%(asctime)s %(levelname)-5.5s [%(requestid)s] [%(process)d] '
                    '[%(name)s][%(threadName)s] %(message)s'))


def setup_newrelic(settings):
    """ If +env+ is not None, setup newrelic and tell it to use that environment config. """
    env = settings.get('newrelic.environment')
    ini_file = settings.get('newrelic.ini')
    if env and ini_file:
        import newrelic.agent
        newrelic.agent.initialize(ini_file, env)
