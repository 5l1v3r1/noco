import binascii
import hashlib
import re
import uuid

import requests
import sentry_sdk
from bs4 import BeautifulSoup
from flask import current_app

import noco.evernote.edam.type.ttypes as Types
from noco.evernote.api.client import EvernoteClient
from noco.evernote.edam.error.ttypes import EDAMUserException

DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/69.0.3497.100 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
    "Accept-Encoding": "gzip, deflate, br",
    "Accept-Language": "zh-CN,zh;q=0.9",
}


def download_html_images(image_url, referer):
    ret = requests.get(image_url, headers={**DEFAULT_HEADERS, "Referer": referer}, )
    if ret.status_code != 200:
        return
    md5_hash = hashlib.md5()
    md5_hash.update(ret.content)
    image_hash = md5_hash.digest()
    return Types.Resource(
        data=Types.Data(bodyHash=image_hash, size=len(ret.content), body=ret.content),
        mime=ret.headers.get("Content-Type"),
    )


def html_enml(html_url, html):
    new_html = (
        html.replace("<br>", "<br/>").replace("<figure>", "").replace("</figure>", "")
    )
    resource_list = []
    soup = BeautifulSoup(new_html, features="html.parser")
    for image_tag in soup.find_all("img"):
        res = download_html_images(image_tag.attrs.get("src"), html_url)
        if not res:
            continue
        image_tag.replace_with(
            soup.new_tag(
                "en-media",
                attrs={
                    "type": res.mime,
                    "hash": binascii.hexlify(res.data.bodyHash).decode(),
                },
            )
        )
        resource_list.append(res)
    ret = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE en-note SYSTEM "http://xml.evernote.com/pub/enml2.dtd">
<en-note>
{soup.prettify()}
</en-note>
    """
    ret = re.sub(r">\s*</en-media>", "/>", ret)
    return ret, resource_list


class Evernote:
    def __init__(self, app=None):
        if app:
            self.init_app(app)
        self.client = None

    def init_app(self, app):
        client = EvernoteClient(
            token=app.config["EVERNOTE_TOKEN"],
            sandbox=app.config["EVERNOTE_SANDBOX"],
            china=app.config["EVERNOTE_CHINA"],
        )
        app.extensions = getattr(app, "extensions", {})
        app.extensions["note"] = self
        app.note = self
        self.client = client
        return client

    def store_note(self, url, title, html) -> bool:
        user_store = self.client.get_user_store()
        content, resources = html_enml(url, html)
        guid = str(uuid.uuid5(uuid.NAMESPACE_URL, url))
        note = Types.Note(
            title=title + f"[{guid}]",
            content=content,
            resources=resources,
            attributes=Types.NoteAttributes(sourceURL=url),
        )
        ret = self.client.find_note(guid, user_store=user_store)
        if ret:
            current_app.logger.info("Ignore existing article")
            return False
        note_store = self.client.get_note_store(user_store=user_store)
        try:
            created_note = note_store.createNote(note)
            current_app.logger.debug(
                "Successfully created a new note with GUID: %s", created_note.guid
            )
        except EDAMUserException as e:
            current_app.logger.error(str(e))
            sentry_sdk.capture_exception(e)
        return True
