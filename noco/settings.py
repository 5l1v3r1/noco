import sentry_sdk
from environs import Env
from sentry_sdk.integrations.celery import CeleryIntegration
from sentry_sdk.integrations.flask import FlaskIntegration

env = Env()
env.read_env()

ENV = env.str("FLASK_ENV", default="production")
DEBUG = ENV == "development"

DIFFBOX_TOKEN = env.str("DIFFBOX_TOKEN")

USE_MAIL = env.bool("USE_MAIL", False)
USE_EVERNOTE = env.bool("USE_EVERNOTE", True)

with env.prefixed("MAIL_"):
    MAIL_SERVER = env.str("SERVER")
    MAIL_USERNAME = env.str("USERNAME")
    MAIL_PASSWORD = env.str("PASSWORD")
    MAIL_PORT = env.int("PORT", 25)
    MAIL_USE_TLS = env.bool("USE_TLS", False)
    MAIL_USE_SSL = env.bool("USE_SSL", False)
    MAIL_DEFAULT_SENDER = env.str("DEFAULT_SENDER")
    MAIL_RECIPIENTS = env.str("RECIPIENTS")

with env.prefixed("EVERNOTE_"):
    EVERNOTE_TOKEN = env.str("TOKEN")
    EVERNOTE_SANDBOX = env.bool("SANDBOX", False)
    EVERNOTE_CHINA = env.bool("CHINA", False)

# Celery

CELERY_BROKER_URL = env.str("CELERY_BROKER_URL")

# Sentry

sentry_sdk.init(
    dsn=env.str("SENTRY_DSN"),
    integrations=[FlaskIntegration(), CeleryIntegration()]
)
