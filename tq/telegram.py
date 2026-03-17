"""Telegram Bot API — send, receive, react. Pure urllib, no deps."""

import json
import urllib.request
import urllib.parse

_config = {"token": None, "chat_id": None}


def configure(token, chat_id):
    _config["token"] = token
    _config["chat_id"] = str(chat_id)


def _api(method, data=None):
    url = f"https://api.telegram.org/bot{_config['token']}/{method}"
    if data:
        body = json.dumps(data).encode()
        req = urllib.request.Request(url, body, {"Content-Type": "application/json"})
    else:
        req = urllib.request.Request(url)
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read())


def get_updates(offset=None, timeout=30):
    params = {"timeout": timeout, "allowed_updates": ["message", "callback_query"]}
    if offset:
        params["offset"] = offset
    result = _api("getUpdates", params)
    return result.get("result", [])


def send(text, reply_to=None):
    data = {
        "chat_id": _config["chat_id"],
        "text": text,
        "parse_mode": "Markdown",
    }
    if reply_to:
        data["reply_parameters"] = {"message_id": reply_to}
    result = _api("sendMessage", data)
    return result.get("result", {}).get("message_id")


def send_plain(text, reply_to=None):
    """Send without markdown parsing — safe for arbitrary text."""
    data = {"chat_id": _config["chat_id"], "text": text}
    if reply_to:
        data["reply_parameters"] = {"message_id": reply_to}
    result = _api("sendMessage", data)
    return result.get("result", {}).get("message_id")


def react(message_id, emoji="👀"):
    try:
        _api("setMessageReaction", {
            "chat_id": _config["chat_id"],
            "message_id": message_id,
            "reaction": [{"type": "emoji", "emoji": emoji}],
        })
    except Exception:
        pass  # reactions are best-effort
