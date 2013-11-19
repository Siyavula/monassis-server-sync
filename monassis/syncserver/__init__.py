from pyramid.config import Configurator

def main(global_config, **settings):
    """
    This function returns a Pyramid WSGI application.
    """
    config = Configurator(
        settings=settings,
    )

    # Include exception logger
    config.include('pyramid_exclog')

    # Set up logging
    import logging.config, os
    logging.config.fileConfig(settings['logging_config'], defaults={'here': os.path.dirname(settings['logging_config']), 'logging_suffix': settings.get('logging_suffix', '')})

    # Entry points
    config.add_route('entry_root', '/')

    config.scan()

    return config.make_wsgi_app()
