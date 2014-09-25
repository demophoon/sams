from calendar import timegm
from datetime import datetime

from pyramid.view import view_config, view_defaults
from pyramid.renderers import get_renderer

from sams import version
from .assets import pingdom as Pingdom
from .models import (
    DBSession,
    Check,
    Outage,
)


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
@view_config(route_name='sams_filtered', renderer='templates/sams.pt')
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


class RequestHandler(object):

    def __init__(self, request):
        self.request = request


@view_defaults(renderer="json")
class ApiViews(RequestHandler):

    def __init__(self, request):
        self.request = request
        RequestHandler.__init__(self, request)

    @view_config(route_name='api_checks')
    @view_config(route_name='api_checks_filtered')
    def checks(self):
        qstring = ''
        try:
            qstring = self.request.params['filter']
        except:
            qstring = ''

        qstring = ''
        if qstring != '':
            query_bu = '%' + qstring  + '%'
            checks = DBSession.query(Check).filter(Check.name.like(query_bu))
            return [{
                'id': x.id,
                'name': x.name,
                'resolution': x.resolution,
                'type': x.type,
                'hostname': x.hostname,
                'updated_at': timegm(x.updated_at.utctimetuple()),
                'created_at': timegm(x.created_at.utctimetuple()),
            } for x in checks]
        else:
            checks = DBSession.query(Check)
            return [{
                'id': x.id,
                'name': x.name,
                'resolution': x.resolution,
                'type': x.type,
                'hostname': x.hostname,
                'updated_at': timegm(x.updated_at.utctimetuple()),
                'created_at': timegm(x.created_at.utctimetuple()),
            } for x in checks]

    @view_config(route_name='api_sams')
    @view_config(route_name='api_sams_filtered')
    def sams(self):
        checks = Pingdom.getChecks()
        filtered_checks = []
        qstring = ''
        try:
            qstring = self.request.params['filter']
        except:
            qstring = ''
        if qstring != '':
            for x in checks:
                if qstring.upper() in x.name:
                    filtered_checks.append(x)
            return [{
                'id': check.id,
                'name': check.name,
                'hostname': check.hostname,
                'status': check.status,
                'created': check.created,
            } for check in filtered_checks]
        else:
            return [{
                    'id': check.id,
                    'name': check.name,
                    'hostname': check.hostname,
                    'status': check.status,
                    'created': check.created,
            } for check in checks]

    @view_config(route_name='api_report')
    def report(self):
        start = datetime.utcfromtimestamp(float(self.request.POST.get('from')))
        end = datetime.utcfromtimestamp(float(self.request.POST.get('to')))
        checks = self.request.POST.getall('check_ids[]')
        outages = DBSession.query(Outage).join(Check).filter(
            Outage.between(start, end)
        )
        if checks:
            outages = outages.filter(Check.id.in_(checks))
        outages = outages.all()
        grouped_outages = {x.check_id: [] for x in outages}
        for outage in outages:
            grouped_outages[outage.check_id].append({
                'id': outage.id,
                'status': outage.status,
                'start': max(
                    timegm(outage.start.utctimetuple()),
                    timegm(start.utctimetuple())
                ),
                'end': min(
                    timegm(outage.end.utctimetuple()),
                    timegm(end.utctimetuple())
                ),
            })
        return grouped_outages

    @view_config(route_name='api_workers', renderer='json')
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


def includeme(config):
    config.include('sams.assets.pingdom')

    # Web Views
    config.add_route('home', '/')
    config.add_route('sams', '/sams')
    config.add_route('sams_filtered', '/sams/{sams_filter}')
    config.add_route('reporting', '/reporting')
    config.add_route('info', '/info')

    # Api Views
    config.add_route('api_sams', '/api/1.0/sams')
    config.add_route('api_sams_filtered', '/api/1.0/sams?filter={sams_filter}')
    config.add_route('api_workers', '/api/1.0/workers')
    config.add_route('api_checks', '/api/1.0/checks')
    config.add_route('api_checks_filtered', '/api/1.0/checks?filter={sams_filter}')
    config.add_route('api_report', '/api/1.0/report')
