from datetime import datetime

import pingdomlib
import transaction
from beaker.cache import cache_region

from sams.models import (
    DBSession,
    Check,
)

Pingdom = None


@cache_region("1m")
def getChecks():
    db_checks = {x.id: x for x in DBSession.query(Check).all()}
    api_checks = Pingdom.getChecks()

    all_checks = {check.id: db_checks.get(check.id, Check(
        id=check.id,
        name=check.name,
        type=check.type,
        hostname=check.hostname,
        resolution=check.resolution,
        created_at=datetime.utcfromtimestamp(check.created),
        updated_at=datetime.utcnow()
    )) for check in api_checks}

    updated_checks = []
    for check in api_checks:
        current_check = all_checks[check.id]
        if not all([
            current_check.name == check.name,
            current_check.type == check.type,
            current_check.hostname == check.hostname,
            current_check.resolution == check.resolution,
            current_check.created_at == datetime.utcfromtimestamp(check.created),
        ]):
            current_check.name = check.name
            current_check.type = check.type
            current_check.hostname = check.hostname
            current_check.resolution = check.resolution
            current_check.created_at = datetime.utcfromtimestamp(check.created)
            current_check.updated_at = datetime.utcnow()
            updated_checks.append(current_check)

    with transaction.manager:
        DBSession.add_all(updated_checks)
    return api_checks


def includeme(config):
    global Pingdom
    settings = config.get_settings()
    Pingdom = pingdomlib.Pingdom(
        settings.get("pingdom_username"),
        settings.get("pingdom_password"),
        settings.get("pingdom_key"),
    )
