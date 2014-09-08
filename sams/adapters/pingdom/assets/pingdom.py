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

from sams.assets.websocket import ClientNotifier

from sams.models import (
    DBSession,
    Check,
    History,
)

logger = logging.getLogger(__name__)


class PingdomWorker(object):

    def __init__(self, settings, helper):
        self.helper = helper
        self.workers = {}
        self.Pingdom = pingdomlib.Pingdom(
            settings.get("username"),
            settings.get("password"),
            settings.get("apikey"),
        )
        self.workers['Pingdom Worker'] = _getChecksWorker.spawn(
            self.Pingdom, self.helper)
        self.workers['Reporting Worker'] = _getOutageInformationWorker.spawn(self.Pingdom)

    @cache_region("1m")
    def getChecks(self):
        """
        A cached function of Pingdom.getChecks to not overload the api
        """
        return self.Pingdom.getChecks()

    def _notify_clients(self, message):
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


class PingdomMonitor:

    def __init__(self, settings, helper):
        self.DBSession = helper
        self.Pingdom = pingdomlib.Pingdom(
            settings.get("username"),
            settings.get("password"),
            settings.get("apikey"),
        )
        self.workers = {
            'Pingdom Worker': _getChecksWorker(self).start(),
            'Reporting Worker': _getOutageInformationWorker(self).start(),
        }

    @cache_region("1m")
    def getChecks(self):
        """
        A cached function of Pingdom.getChecks to not overload the api
        """
        return self.Pingdom.getChecks()


class _getChecksWorker(Greenlet):
    """
    A background worker for notifying clients connected via websocket of pingdom
    status changes

    Someone has to do the work and we can take care of it for many clients
    instead of all the clients coming to us for status updates every minute.
    """

    def __init__(self, helper, sleep_time=60):
        self.helper = helper
        self.sleep_time = sleep_time
        self.last_update = datetime.utcnow()
        self.previous_state = {x.id: x for x in self.helper.getChecks()}
        Greenlet.__init__(self)

    def fetch_information(self):
        logging.info("Updating check information")
        with transaction.manager:
            api_checks = self.helper.getChecks()
            db_checks = self.helper.DBSession.query(Check).all()

            api_ids = set([str(check.id) for check in api_checks])
            db_ids = set([str(check.id) for check in db_checks])

            new_checks = api_ids - db_ids
            api_checks = {str(check.id): check for check in api_checks}

            print new_checks

            updated_checks = []

            for check in new_checks:
                api_check = api_checks.get(check)
                check = self.helper.DBSession.create_check(
                    id=str(api_check.id),
                    name=api_check.name,
                    type=api_check.type,
                    hostname=api_check.hostname,
                    resolution=api_check.resolution,
                    created_at=datetime.utcfromtimestamp(api_check.created),
                    updated_at=datetime.utcnow(),
                )
                updated_checks.append(
                    check
                )
            if updated_checks:
                DBSession.add_all(updated_checks)
        pass


    def fetch_information2(self):
        with transaction.manager:
            logging.info("Updating check information")
            api_checks = self.Pingdom.getChecks()

            status_changes = {}
            for check in api_checks:
                if not self.previous_state.get(check.id).status == check.status:
                    status_changes[str(check.id)] = check.status
            self.previous_state = {x.id: x for x in api_checks}
            if status_changes:
                _notify_clients(status_changes)

            db_checks = {x.id: x for x in DBSession.query(Check).all()}
            updated_checks = []
            for check in api_checks:
                if str(check.id) not in db_checks:
                    updated_checks.append(
                        Check(
                            id=str(check.id),
                            name=check.name,
                            type=check.type,
                            hostname=check.hostname,
                            resolution=check.resolution,
                            created_at=datetime.utcfromtimestamp(check.created),
                            updated_at=datetime.utcnow(),
                        )
                    )
                elif not all([
                    db_checks[str(check.id)].name == check.name,
                    db_checks[str(check.id)].type == check.type,
                    db_checks[str(check.id)].hostname == check.hostname,
                    db_checks[str(check.id)].resolution == check.resolution,
                ]):
                    db_checks[str(check.id)].name = check.name
                    db_checks[str(check.id)].type = check.type
                    db_checks[str(check.id)].hostname = check.hostname
                    db_checks[str(check.id)].resolution = check.resolution
                    updated_checks.append(db_checks[check])
            if updated_checks:
                DBSession.add_all(updated_checks)
                DBSession.flush()

    def _run(self):
        while True:
            self.fetch_information()
            try:
                pass
            except Exception as e:
                logger.warn(e)
                raise e
            self.last_update = datetime.utcnow()
            gevent.sleep(self.sleep_time)


class _getOutageInformationWorker(Greenlet):
    """
    Periodically fetches new information about outages to keep our database up
    to date with Pingdom.

    Allows for speedy reports.
    """

    def __init__(self, pingdom, sleep_time=900):
        self.Pingdom = pingdom
        self.sleep_time = sleep_time
        self.state = "initialization"
        self.percent = 0.0
        self.percent_rate = 0.0
        self.last_percentage_update = datetime.utcnow()
        self.last_sleep = datetime.utcnow()
        self.current_check = None
        Greenlet.__init__(self)


    def fetch_information(self):
        pass

    def fetch_information2(self):
        with transaction.manager:
            api_checks = {x.id: x for x in self.Pingdom.getChecks()}
            checks = DBSession.query(Check).all()
            total_checks = len(checks)
            for index, check in enumerate(checks):
                percentage_delta = (float(index) / float(total_checks)) - self.percent
                time_delta = datetime.utcnow() - self.last_percentage_update
                self.percent_rate = percentage_delta / time_delta.total_seconds()
                self.percent = float(index) / float(total_checks)
                self.last_percentage_update = datetime.utcnow()
                self.current_check = check.name
                updates = []
                logging.info("Fetching Historical Data for %s (%d/%d) -- %10.2f" % (
                    check.name,
                    index,
                    total_checks,
                    int(self.percent * 1000) / 10.0,
                ))
                latest = DBSession.query(History).filter(
                    History.check_id == check.id
                ).order_by(History.end.desc()).first()
                if latest:
                    time_from = int(calendar.timegm(latest.end.utctimetuple()))
                    DBSession.delete(latest)
                else:
                    time_from = calendar.timegm(check.created_at.utctimetuple())
                    updates.append(
                        History(
                            check_id=check.id,
                            start=datetime.utcfromtimestamp(0),
                            end=check.created_at,
                            status='unknown',
                            updated_at=datetime.utcnow(),
                        )
                    )
                if calendar.timegm(datetime.utcnow().utctimetuple()) - time_from < self.sleep_time * 2:
                    continue
                time_to = int(calendar.timegm(datetime.utcnow().utctimetuple()))
                params = {"from": time_from, "to": time_to}
                api_check = api_checks.get(check.id)
                if not api_check:
                    continue
                outages = api_check.outages(**params)
                for outage in outages:
                    updates.append(History(
                        check_id=check.id,
                        start=datetime.utcfromtimestamp(outage['timefrom']),
                        end=datetime.utcfromtimestamp(outage['timeto']),
                        status=outage['status'],
                        updated_at=datetime.utcnow(),
                    ))
                if updates:
                    logger.info("%d rows added." % (len(updates)))
                    DBSession.add_all(updates)
                    DBSession.flush()
            self.percent = 1.0
            self.percent_rate = 0.0

    def _run(self):
        while True:
            self.state = "running"
            self.fetch_information()
            try:
                pass
            except Exception as e:
                logger.warn(e)
                raise e
            transaction.commit()
            self.state = "sleeping"
            self.last_sleep = datetime.utcnow()
            gevent.sleep(self.sleep_time)


def includeme(config):
    """
    Pyramid Bootstrap
    """
    config.add_route('api_workers', '/api/1.0/workers')
