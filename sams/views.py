from calendar import timegm

from pyramid.view import view_config
from pyramid.renderers import get_renderer

from sams import version
from .assets import pingdom as Pingdom


def layout():
    renderer = get_renderer('templates/main.pt')
    layout = renderer.implementation().macros['layout']
    return layout


@view_config(route_name='home', renderer='templates/index.pt')
def home(request):
    return {
        'layout': layout(),
        'title': 'Home',
    }


@view_config(route_name='sams', renderer='templates/sams.pt')
def sams(request):
    return {}


@view_config(route_name='reporting', renderer='templates/reporting.pt')
def reporting(request):
    return {
        'layout': layout(),
        'title': 'Reporting',
    }


@view_config(route_name='info', renderer='templates/info.pt')
def info(request):
    return {
        'layout': layout(),
        'title': 'Reporting',
        'version': version,
    }


@view_config(route_name='worker_info', renderer='json')
def worker_info(request):
    return {
        "pingdom_worker": {
            "last_update": timegm(Pingdom.workers["Pingdom Worker"].last_update.utctimetuple()),
            "sleep_time": Pingdom.workers["Pingdom Worker"].sleep_time,
        },
        "reporting_worker": {
            "state": Pingdom.workers["Reporting Worker"].state,
            "percent": Pingdom.workers["Reporting Worker"].percent,
            "percent_rate": Pingdom.workers["Reporting Worker"].percent_rate,
            "current_check": Pingdom.workers["Reporting Worker"].current_check,
            "last_sleep": timegm(Pingdom.workers["Reporting Worker"].last_sleep.utctimetuple()),
            "sleep_time": Pingdom.workers["Reporting Worker"].sleep_time,
        }
    }


@view_config(route_name='api_sams', renderer='json')
def api_sams(request):
    checks = Pingdom.getChecks()
    return [{
        'id': check.id,
        'name': check.name,
        'hostname': check.hostname,
        'status': check.status,
        'created': check.created,
    } for check in checks]


def includeme(config):
    config.include('sams.assets.pingdom')

    # Web Views
    config.add_route('home', '/')
    config.add_route('sams', '/sams')
    config.add_route('reporting', '/reporting')
    config.add_route('info', '/info')

    # Api Views
    config.add_route('api_sams', '/api/1.0/sams')
    config.add_route('worker_info', '/api/1.0/workers')
