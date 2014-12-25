import os
import pkgutil

from pyramid.config import Configurator
from sqlalchemy import engine_from_config

from .models import (
    DBSession,
    Base,
)

from .assets.websocket import ClientNotifier

version = (0, 0, '0 alpha')


def main(global_config, **settings):
    """ This function returns a Pyramid WSGI application.
    """
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
    monitors = []
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
    from conf import pingdom
    for monitor in pingdom.monitors:
        adapter = adapters.get(monitor['adapter'])
        if not adapter:
            raise Exception("Adapter '%s' is not implemented" % (
                monitor['adapter'])
            )
        monitors.append(adapter.configure_monitor(**monitor))
    return config.make_wsgi_app()
