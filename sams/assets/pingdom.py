import gevent
from gevent import monkey, Greenlet
monkey.patch_all()

import logging
import calendar
import json
from datetime import datetime

import transaction
import pingdomlib
from beaker.cache import cache_region

from websocket import ClientNotifier

from sams.models import (
    DBSession,
    Check,
    Outage,
)

logger = logging.getLogger(__name__)
Pingdom = None
workers = []


@cache_region("1m")
def getChecks():
    return Pingdom.getChecks()


def _notify_clients(message):
    for client in ClientNotifier.all_clients:
        payload = {
            'created_at': int(calendar.timegm(datetime.utcnow().utctimetuple())),
            'data': message,
        }
        client.send(json.dumps(payload))



class _getChecksWorker(Greenlet):

    def __init__(self):
        self.previous_state = {x.id: x for x in Pingdom.getChecks()}
        Greenlet.__init__(self)

    def _run(self):
        while True:
            with transaction.manager:
                logging.info("Updating check information")
                api_checks = getChecks()

                status_changes = {}
                for check in api_checks:
                    if not self.previous_state.get(check.id).status == check.status:
                        status_changes[check.id] = check.status
                self.previous_state = {x.id: x for x in api_checks}
                if status_changes:
                    _notify_clients(status_changes)

                db_checks = {x.id: x for x in DBSession.query(Check).all()}
                updated_checks = []
                for check in api_checks:
                    if check.id not in db_checks:
                        updated_checks.append(
                            Check(
                                id=check.id,
                                name=check.name,
                                type=check.type,
                                hostname=check.hostname,
                                resolution=check.resolution,
                                created_at=datetime.utcfromtimestamp(check.created),
                                updated_at=datetime.utcnow(),
                            )
                        )
                    elif not all([
                        db_checks[check.id].name == check.name,
                        db_checks[check.id].type == check.type,
                        db_checks[check.id].hostname == check.hostname,
                        db_checks[check.id].resolution == check.resolution,
                    ]):
                        db_checks[check.id].name = check.name
                        db_checks[check.id].type = check.type
                        db_checks[check.id].hostname = check.hostname
                        db_checks[check.id].resolution = check.resolution
                        updated_checks.append(db_checks[check])
                if updated_checks:
                    DBSession.add_all(updated_checks)
                    DBSession.flush()

            gevent.sleep(15)


class _getOutageInformationWorker(Greenlet):

    def __init__(self, sleep_time=900):
        self.sleep_time = sleep_time
        Greenlet.__init__(self)

    def _run(self):
        logging.info("Worker Started")
        while True:
            with transaction.manager:
                api_checks = {x.id: x for x in getChecks()}
                checks = DBSession.query(Check).all()
                for check in checks:
                    logging.info("Fetching Historical Data for " + check.name)
                    latest = DBSession.query(Outage).filter(
                        Outage.check_id == check.id
                    ).order_by(Outage.end.desc()).first()
                    if latest:
                        time_from = int(calendar.timegm(latest.start.utctimetuple()))
                        DBSession.delete(latest)
                    else:
                        time_from = calendar.timegm(check.created_at.utctimetuple())
                    if calendar.timegm(datetime.utcnow().utctimetuple()) - time_from < self.sleep_time:
                        continue
                    time_to = int(calendar.timegm(datetime.utcnow().utctimetuple()))
                    params = {"from": time_from, "to": time_to}
                    api_check = api_checks.get(check.id)
                    updates = []
                    outages = api_check.outages(**params)
                    for outage in outages:
                        updates.append(Outage(
                            check_id=check.id,
                            start=datetime.utcfromtimestamp(outage['timefrom']),
                            end=datetime.utcfromtimestamp(outage['timeto']),
                            status=outage['status'],
                            updated_at=datetime.utcnow(),
                        ))
                    if updates:
                        DBSession.add_all(updates)
                        DBSession.flush()
            gevent.sleep(self.sleep_time)


def includeme(config):
    global Pingdom
    global workers
    settings = config.get_settings()
    Pingdom = pingdomlib.Pingdom(
        settings.get("pingdom_username"),
        settings.get("pingdom_password"),
        settings.get("pingdom_key"),
    )
    workers.append(_getChecksWorker.spawn())
    workers.append(_getOutageInformationWorker.spawn())
