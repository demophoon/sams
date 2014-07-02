from pyramid.config import Configurator
from sqlalchemy import engine_from_config

from .models import (
    DBSession,
    Base,
)

from .assets.websocket import ClientNotifier


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
    return config.make_wsgi_app()
