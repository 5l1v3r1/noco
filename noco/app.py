import logging
import sys

from flask import Flask, jsonify, current_app, request

from noco.diffbot import DiffbotClient
from noco.extensions import mail, note, celery
from noco.tasks import send_mail, send_note


def configure_logger(app):
    """Configure loggers."""
    handler = logging.StreamHandler(sys.stdout)
    if not app.logger.handlers:
        app.logger.addHandler(handler)


def register_errorhandlers(app):
    """Register error handlers."""

    def render_error(error):
        """Render error template."""
        # If a HTTPException, pull the `code` attribute; default to 500
        error_code = getattr(error, "code", 500)
        return jsonify({"error": str(error), "code": error_code}), error_code

    for errcode in [401, 404, 500]:
        app.errorhandler(errcode)(render_error)
    return None


def register_extensions(app):
    mail.init_app(app)
    note.init_app(app)


def init_celery(app=None):
    app = app or create_app()
    celery.conf.broker_url = app.config["CELERY_BROKER_URL"]
    celery.conf.update(app.config)

    class ContextTask(celery.Task):
        """Make celery tasks work with Flask app context"""

        def __call__(self, *args, **kwargs):
            with app.app_context():
                return self.run(*args, **kwargs)

    celery.Task = ContextTask
    return celery


def register_blueprints(app: Flask):
    @app.route("/parser", methods=["GET"])
    def parser():
        url = request.args.get("url", None)
        if not url:
            return jsonify({"content": "Not found"})
        ret = DiffbotClient().request(
            url,
            current_app.config["DIFFBOX_TOKEN"],
            "article",
            fields=["title", "html"],
        )
        if not ret["objects"]:
            return jsonify({"content": "Not found"})
        title = "Error"
        html = ""
        try:
            title = ret["objects"][0]["title"]
            html = ret["objects"][0]["html"]
            if current_app.config["USE_MAIL"]:
                send_mail.apply_async(kwargs=dict(title=title, html=html))

            if current_app.config["USE_EVERNOTE"]:
                send_note.apply_async(kwargs=dict(url=url, title=title, html=html))
        except Exception as e:
            current_app.logger.exception("Error while parsing: " + url)
        return jsonify({"title": title, "content": html})


def create_app(config_object="noco.settings"):
    """Create application factory, as explained here: http://flask.pocoo.org/docs/patterns/appfactories/.
    :param config_object: The configuration object to use.
    """
    app = Flask(__name__.split(".")[0])
    app.config.from_object(config_object)
    register_extensions(app)
    register_blueprints(app)
    register_errorhandlers(app)
    configure_logger(app)
    return app
