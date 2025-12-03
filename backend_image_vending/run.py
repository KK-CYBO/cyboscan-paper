from api import create_app
from gunicorn.app.base import BaseApplication
import os

app = create_app()


class StandaloneApplication(BaseApplication):
    def __init__(self, app, options=None):
        self.application = app
        self.options = options or {}
        super().__init__()

    def load_config(self):
        config = {
            key: value
            for key, value in self.options.items()
            if key in self.cfg.settings and value is not None
        }
        for key, value in config.items():
            self.cfg.set(key.lower(), value)

    def load(self):
        return self.application


if __name__ == "__main__":
    port = os.environ.get("PORT", "5000")

    options = {
        "bind": f"0.0.0.0:{port}",
        "workers": 3,
        "threads": 10,
        "worker_class": "gevent",
        "loglevel": "info",
    }

    StandaloneApplication(app, options).run()
