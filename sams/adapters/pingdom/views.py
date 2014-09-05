from calendar import timegm

from pyramid.view import view_config, view_defaults

from assets import pingdom as Pingdom


class RequestHandler(object):

    def __init__(self, request):
        self.request = request


@view_defaults(renderer="json")
class ApiViews(RequestHandler):

    def __init__(self, request):
        self.request = request
        RequestHandler.__init__(self, request)

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


