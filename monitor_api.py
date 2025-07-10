#!/usr/bin/env python3
"""
Poll the API record every run.
If the JSON differs from the last saved copy (`study.json`),
send yourself an e-mail and overwrite the file.

Required secrets (exposed as env vars by the workflow):
  EMAIL_USER       – your full Gmail address
  EMAIL_PASSWORD   – Gmail App-Password (not your login pwd)
  RECIPIENT        – where the alert should go (hard-coded below too)
  API_URL          – API URL to monitor
"""

import difflib
import json
import os
import smtplib
import ssl
from email.message import EmailMessage

import requests

FILE = "study.json"

def fetch_latest():
    resp = requests.get(url=os.getenv("API_URL"))
    resp.raise_for_status()
    return resp.json()


def load_previous():
    if os.path.isfile(FILE):
        with open(FILE, "r") as fh:
            return json.load(fh)
    return None


def email_update(diff_text: str):
    msg = EmailMessage()
    user, pwd, to_addr = map(os.getenv, ("EMAIL_USER", "EMAIL_PASSWORD", "RECIPIENT"))
  
    msg["Subject"] = "API Update Detected"
    msg["From"] = user
    msg["To"] = to_addr
    msg.set_content(
        "The record changed.\n\nUnified diff (truncated to 5 000 chars):\n\n"
        + diff_text[:5000]
    )

    with smtplib.SMTP("smtp.gmail.com", 587) as s:
      s.starttls(context=ssl.create_default_context())
      s.login(user, pwd)
      s.send_message(msg)
    print("Alert e-mail sent.")


def save_latest(data):
    with open(FILE, "w") as fh:
        json.dump(data, fh, indent=2, sort_keys=True)
    print("Saved new copy to", FILE)


def main():
    latest = fetch_latest()
    previous = load_previous()

    if previous != latest:
        # Build a human-readable diff for the e-mail body
        diff = ""
        if previous is not None:
            prev_lines = json.dumps(previous, indent=2, sort_keys=True).splitlines()
            new_lines  = json.dumps(latest,   indent=2, sort_keys=True).splitlines()
            diff = "\n".join(difflib.unified_diff(prev_lines, new_lines, lineterm=""))
        else:
            diff = "No previous snapshot existed; this is the first run."

        email_update(diff)
        save_latest(latest)
    else:
        print("No change detected.")


if __name__ == "__main__":
    main()
