import requests
import time
import json

MAILTM_HEADERS = {   
    "Accept": "application/json",
    "Content-Type": "application/json" 
}

class MailTmError(Exception):
    pass

def _make_mailtm_request(request_fn, timeout = 600):
    tstart = time.monotonic()
    error = None
    status_code = None
    while time.monotonic() - tstart < timeout:
        try:
            r = request_fn()
            status_code = r.status_code
            if status_code == 200 or status_code == 201:
                return r.json()
            if status_code != 429:
                break
        except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
            error = e
        time.sleep(1.0)

    if error is not None:
        raise MailTmError(error) from error
    if status_code is not None:
        raise MailTmError(f"Status code: {status_code}")
    if time.monotonic() - tstart >= timeout:
        raise MailTmError("timeout")
    raise MailTmError("unknown error")

def get_mailtm_domains():
    def _domain_req():
        return requests.get("https://api.mail.tm/domains", headers = MAILTM_HEADERS)

    r = _make_mailtm_request(_domain_req)

    return [ x['domain'] for x in r ]

def create_mailtm_account(address, password):
    account = json.dumps({"address": address, "password": password})   
    def _acc_req():
        return requests.post("https://api.mail.tm/accounts", data=account, headers=MAILTM_HEADERS)

    r = _make_mailtm_request(_acc_req)
    assert len(r['id']) > 0

def get_mailtm_token(address, password):
    account = json.dumps({"address": address, "password": password})
    def _token_req():
        return requests.post("https://api.mail.tm/token", data=account, headers=MAILTM_HEADERS)

    r = _make_mailtm_request(_token_req)
    return r["token"]

def get_mailtm_account_id(token):
    headers = {"Authorization": "Bearer " + token}
    def _acc_id_req():
        return requests.get("https://api.mail.tm/accounts", headers=headers)

    r = _make_mailtm_request(_acc_id_req)
    return r["hydra:member"][0]["id"]

def get_latest_email(token, account_id):
    headers = {"Authorization": "Bearer " + token}
    def _email_req():
        return requests.get("https://api.mail.tm/messages", headers=headers, params={"to": account_id})

    r = _make_mailtm_request(_email_req)
    messages = r["hydra:member"]

    if not messages:
        return None

    latest_message_id = messages[0]["id"]

    def _email_detail_req():
        return requests.get("https://api.mail.tm/messages/" + latest_message_id, headers=headers)

    latest_message = _make_mailtm_request(_email_detail_req)

    return latest_message

server_url = "http://localhost:18000"

email = "arbnihppow@wireconnected.com"
password = "5'^wioiv"

token = get_mailtm_token(email, password)

account_id = get_mailtm_account_id(token)

last_seen_email_id = None


while True:
    latest_email = get_latest_email(token, account_id)

    if latest_email is None:
        continue
    latest_email_id = latest_email["id"]

    if latest_email_id != last_seen_email_id:
        latest_email_subject = latest_email["subject"]
        latest_email_content = latest_email["text"]

        requests.post(server_url, json={"subject": latest_email_subject, "content": latest_email_content})
        last_seen_email_id = latest_email_id

    time.sleep(10)
