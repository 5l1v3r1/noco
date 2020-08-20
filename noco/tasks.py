from celery import current_app
from flask_mail import Message

from noco.extensions import celery, mail, note


@celery.task
def send_mail(title, html):
    mail.send(
        Message(
            subject="【RSS】" + title,
            sender=("RSS Sender", current_app.conf["MAIL_USERNAME"]),
            recipients=current_app.conf["MAIL_RECIPIENTS"].split(","),
            html=html.replace("<img ", '<img referrerpolicy="no-referrer" ').replace(
                "<image ", '<image referrerpolicy="no-referrer" '
            ),
        )
    )


@celery.task
def send_note(url, title, html):
    note.store_note(url, title, html)
