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
            "report_worker": {
                "state": Pingdom.workers["Report Worker"].state,
                "percent": Pingdom.workers["Report Worker"].percent,
                "percent_rate": Pingdom.workers["Report Worker"].percent_rate,
                "current_check": Pingdom.workers["Report Worker"].current_check,
                "last_sleep": timegm(Pingdom.workers["Report Worker"].last_sleep.utctimetuple()),
                "sleep_time": Pingdom.workers["Report Worker"].sleep_time,
            }
        }
