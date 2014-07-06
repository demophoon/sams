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
workers = {}


@cache_region("1m")
def getChecks():
    """
    A cached function of Pingdom.getChecks to not overload the api
    """
    return Pingdom.getChecks()


def _notify_clients(message):
    """
    Relays a message via websockets to all connected clients about Pingdom
    status changes

    :message: Any JSON serializable datatype
    """
    for client in ClientNotifier.all_clients:
        payload = {
            'created_at': int(calendar.timegm(
                datetime.utcnow().utctimetuple())),
            'data': message,
        }
        client.send(json.dumps(payload))


class _getChecksWorker(Greenlet):
    """
    A background worker for notifying clients connected via websocket of pingdom
    status changes

    Someone has to do the work and we can take care of it for many clients
    instead of all the clients coming to us for status updates every minute.
    """

    def __init__(self, sleep_time=15):
        self.sleep_time = sleep_time
        self.last_update = datetime.utcnow()
        self.previous_state = {x.id: x for x in Pingdom.getChecks()}
        Greenlet.__init__(self)

    def fetch_information(self):
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

    def _run(self):
        while True:
            try:
                self.fetch_information()
            except Exception as e:
                logger.warn(e)
            self.last_update = datetime.utcnow()
            gevent.sleep(self.sleep_time)


class _getOutageInformationWorker(Greenlet):
    """
    Periodically fetches new information about outages to keep our database up
    to date with Pingdom.

    Allows for speedy reports.
    """

    def __init__(self, sleep_time=900):
        self.sleep_time = sleep_time
        self.state = "initialization"
        self.percent = 0.0
        self.percent_rate = 0.0
        self.last_percentage_update = datetime.utcnow()
        self.last_sleep = datetime.utcnow()
        self.current_check = None
        Greenlet.__init__(self)

    def fetch_information(self):
        with transaction.manager:
            api_checks = {x.id: x for x in getChecks()}
            checks = DBSession.query(Check).all()
            total_checks = len(checks)
            for index, check in enumerate(checks):
                percentage_delta = (float(index) / float(total_checks)) - self.percent
                time_delta = datetime.utcnow() - self.last_percentage_update
                self.percent_rate = percentage_delta / time_delta.total_seconds()
                self.percent = float(index) / float(total_checks)
                self.last_percentage_update = datetime.utcnow()
                self.current_check = check.name
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
                if not api_check:
                    continue
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
            self.percent = 1.0
            self.percent_rate = 0.0

    def _run(self):
        while True:
            self.state = "running"
            try:
                self.fetch_information()
            except Exception as e:
                logger.warn(e)
            self.state = "sleeping"
            self.last_sleep = datetime.utcnow()
            gevent.sleep(self.sleep_time)


def includeme(config):
    """
    Pyramid Bootstrap
    """
    global Pingdom
    global workers
    settings = config.get_settings()
    Pingdom = pingdomlib.Pingdom(
        settings.get("pingdom_username"),
        settings.get("pingdom_password"),
        settings.get("pingdom_key"),
    )
    workers['Pingdom Worker'] = _getChecksWorker.spawn()
    workers['Reporting Worker'] = _getOutageInformationWorker.spawn()
