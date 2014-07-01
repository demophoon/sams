from pyramid.view import view_config

from .assets import pingdom as Pingdom


@view_config(route_name='home', renderer='templates/index.pt')
def home(request):
    return {}


@view_config(route_name='sams', renderer='templates/sams.pt')
def sams(request):
    return {}


@view_config(route_name='api_sams', renderer='json')
def api_sams(request):
    checks = Pingdom.getChecks()
    print dir(checks[0])
    return [{
        'id': check.id,
        'name': check.name,
        'hostname': check.hostname,
        'status': check.status,
    } for check in checks]


def includeme(config):
    config.include('sams.assets.pingdom')
    config.add_route('home', '/')
    config.add_route('sams', '/sams')
    config.add_route('api_sams', '/api/1.0/sams')
