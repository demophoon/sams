import os
import pkgutil
import ConfigParser

from pyramid.config import Configurator
from sqlalchemy import engine_from_config

from .models import (
    DBSession,
    Base,
)

from .assets.websocket import ClientNotifier

version = (0, 0, '0 alpha')

# Monitors
monitors = {}


def main(global_config, **settings):
    """ This function returns a Pyramid WSGI application.
    """
    global monitors
    engine = engine_from_config(settings, 'sqlalchemy.')
    DBSession.configure(bind=engine)
    Base.metadata.bind = engine
    config = Configurator(settings=settings)

    config.include('pyramid_chameleon')
    config.include('pyramid_beaker')
    config.include('pyramid_sockjs')
    config.include('sams.views')
    config.add_static_view('static', 'static', cache_max_age=3600)

    config.add_sockjs_route(prefix='/api/1.0/sams/ws', session=ClientNotifier)

    config.scan()

    adapter_path = os.path.join(os.path.dirname(__file__), 'adapters')
    adapters = {}

    for loader, mod_name, ispkg in pkgutil.iter_modules(path=[adapter_path]):
        if ispkg:
            adapters[mod_name] = __import__(
                'sams.adapters.%s' % (mod_name), fromlist=['*']
            )
            try:
                adapters[mod_name].includeme(config)
            except AttributeError:
                # No initial setup hook
                pass
    print adapters

    # Parse Config Files
    config_load_path = [
        os.path.join(
            os.path.abspath(os.path.dirname(__file__)), 'conf/sams.conf'),
        os.path.expanduser('~/.sams.conf'),
    ]
    monitor_config = ConfigParser.ConfigParser()
    print config_load_path
    monitor_config.read(config_load_path)
    for monitor in monitor_config.sections():
        adapter = adapters.get(monitor_config.get(monitor, 'adapter'))
        if not adapter:
            raise Exception("Adapter '%s' is not implemented" % (
                monitor_config.get(monitor, 'adapter'))
            )
        monitor_args = {k: v for k, v in monitor_config.items(monitor)}
        monitors[monitor] = adapter.configure_monitor(**monitor_args)
        monitors[monitor].name = monitor

    return config.make_wsgi_app()
