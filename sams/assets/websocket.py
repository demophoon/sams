import json

from pyramid_sockjs.session import Session


class ClientNotifier(Session):
    all_clients = []

    def __init__(self, *args, **kwargs):
        Session.__init__(self, *args, **kwargs)

    def on_open(self):
        self.all_clients.append(self)
        pass

    def on_message(self, message):
        pass

    def on_close(self):
        self.all_clients.remove(self)
        pass
