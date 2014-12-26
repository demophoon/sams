import calendar
from datetime import datetime

from pyramid.view import view_config

from sams.adapters import common


@view_config(renderer='json', route_name='api_manual_status')
@common.get_monitor
def api_manual_status(context, request):
    params = dict(request.GET)
    if 'time' not in params:
        params['time'] = int(calendar.timegm(datetime.utcnow().utctimetuple()))

    if request.monitor:
        check = [x for x in request.monitor.get_list() if x.id == params['id']]
        if check:
            check[0].status = params['status']

    return params


def includeme(config):
    config.add_route('api_manual_status', '/api/1.0/manual_status')


class ManualMonitor(common.SamsAdapter):
    pass

def configure_monitor(**kwargs):
    new_monitor = ManualMonitor()
    checks = kwargs.get('checks', '').strip().split("\n")
    for check_id in checks:
        new_monitor.checks.append(common.SamsCheck(id=check_id))
    return new_monitor
