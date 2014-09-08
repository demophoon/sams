import os

import yaml
from pyramid.config import Configurator
from sqlalchemy import engine_from_config

from .models import (
    DBSession,
    Base,
    AdapterHelper,
)

from .assets.websocket import ClientNotifier

version = (0, 0, '0 alpha')

monitors = []


def main(global_config, **settings):
    global monitors
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

    adapter_dir = './sams/adapters'

    adapter_paths = []
    for adapter in os.listdir(adapter_dir):
        if os.path.isdir(adapter_dir + os.sep + adapter):
            module_dir = adapter_dir + os.sep + adapter
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

    conf_dir = './sams/conf'

    conf_paths = []
    for conf in [x for x in os.listdir(conf_dir) if x.endswith(".conf")]:
        if os.path.isfile(conf_dir + os.sep + conf):
            monitor_dir = os.path.abspath(conf_dir + os.sep + conf)
            conf_paths.append(monitor_dir)
    print conf_paths
    for conf in conf_paths:
        monitor_config = yaml.load(open(conf, "r"))
        for monitor in monitor_config['monitors']:
            current_monitor = monitor_config['monitors'][monitor]
            adapter = adapters.get(current_monitor['monitor'])
            helper = AdapterHelper(current_monitor['monitor'], monitor)
            monitors.append(
                adapter.initialize(current_monitor, helper)
            )

    config.scan()
    return config.make_wsgi_app()
