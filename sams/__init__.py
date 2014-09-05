import os

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

    base_dir = './sams/adapters'
    adapter_paths = []
    for adapter in os.listdir(base_dir):
        if os.path.isdir(base_dir + os.sep + adapter):
            module_dir = base_dir + os.sep + adapter
            if os.path.exists(module_dir + os.sep + '__init__.py'):
                adapter_paths.append(adapter)
    adapters = {}
    for adapter in adapter_paths:
        adapters[adapter] = __import__(
            "sams.adapters.%s" % adapter, fromlist=["*"]
        )
        try:
            adapters[adapter].entrypoint(config)
        except Exception as e:
            print e

    print adapters

    config.scan()
    return config.make_wsgi_app()
