from pyramid.view import view_config

from .models import (
    DBSession,
)


@view_config(route_name='home', renderer='templates/index.pt')
def home(request):
    return {}


@view_config(route_name='sams', renderer='templates/sams.pt')
def sams(request):
    return {}


def includeme(config):
    config.add_route('home', '/')
    config.add_route('sams', '/sams')
