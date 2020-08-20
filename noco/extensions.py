from celery import Celery
from flask_mail import Mail

from noco.note_ext import Evernote

mail = Mail()
note = Evernote()
celery = Celery()
