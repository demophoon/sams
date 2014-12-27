from sams import monitors
from sams.models import DBSession


class SamsAdapter(object):

    """
    Helper class for creating more adapters
    """

    DBSession = DBSession

    def __init__(self):
        self.name = None
        self._checks = SamsCheckList()

    @property
    def checks(self):
        return self._checks

    @checks.setter
    def checks(self, value):
        if not isinstance(value, SamsCheckList):
            raise TypeError("item is not of type SamsCheckList")

    def get_list(self):
        """
        This method is for retrieving a list of checks that the adapter is aware
        of.
        """
        return self.checks

    def commit(self):
        """
        This method is used to commit all changes to all the checks that this
        adapter owns.
        """
        return NotImplemented


class SamsCheckList(list):

    def append(self, item):
        if not isinstance(item, SamsCheck):
            raise TypeError("item is not of type SamsCheck")
        super(SamsCheckList, self).append(item)


class SamsCheck(object):

    """
    Helper class for creating checks which Sams maps to database objects.
    """

    required_attrs = [
        'id',
    ]

    def __setattr__(self, name, value):
        if name == 'status':
            print 'Status attribute set'
        super(SamsCheck, self).__setattr__(name, value)

    def __getattr__(self, name):
        try:
            return super(SamsCheck, self).__getattr__(name)
        except:
            return None

    def __init__(self, **kwargs):
        if not any([x in kwargs for x in self.required_attrs]):
            raise ValueError('Missing Required Attributes')
        if 'status' not in kwargs:
            kwargs['status'] = 'unknown'
        for k, v in kwargs.items():
            setattr(self, k, v)

    def commit(self):
        return NotImplemented


def get_monitor(fn):
    def new_function(*args, **kwargs):
        context, request = args
        print request.GET
        monitor = request.matchdict.get('monitor')
        if monitor:
            request.monitor = monitors.get(monitor)
        else:
            request.monitor = None
        return fn(context, request)
    return new_function
