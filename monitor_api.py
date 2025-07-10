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
  WEBSITE_URL      – Website URL to monitor
"""

import difflib
import json
from bs4 import BeautifulSoup
import os
import smtplib
import ssl
from email.message import EmailMessage

import requests

JSON_FILE = "study.json"
HTML_FILE = "website.html"

def fetch_latest_json():
    resp = requests.get(url=os.getenv("API_URL"))
    resp.raise_for_status()
    return resp.json()

def fetch_latest_html():
    resp = requests.get(url=os.getenv("WEBSITE_URL"))
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")
    return soup.prettify()
    
def load_previous_json():
    if os.path.isfile(JSON_FILE):
        with open(JSON_FILE, "r") as fh:
            return json.load(fh)
    return None

def load_previous_html():
    if os.path.isfile(HTML_FILE):
        with open(HTML_FILE, "r", encoding="utf-8") as fh:
            return fh.read()
    return None

def email_update(diff_text: str, subject: str):
    msg = EmailMessage()
    user, pwd, to_addr = map(os.getenv, ("EMAIL_USER", "EMAIL_PASSWORD", "RECIPIENT"))
  
    msg["Subject"] = subject
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


def save_latest_json(data, file_path):
    with open(file_path, "w") as fh:
        json.dump(data, fh, indent=2, sort_keys=True)
    print("Saved new copy to", file_path)

def save_latest_html(data, file_path):
    with open(file_path, "w", encoding="utf-8") as fh:
        fh.write(data)
    print("Saved new copy to", file_path)

def main():
    latest = fetch_latest_json()
    previous = load_previous_json()

    if previous != latest:
        # Build a human-readable diff for the e-mail body
        diff = ""
        if previous is not None:
            prev_lines = json.dumps(previous, indent=2, sort_keys=True).splitlines()
            new_lines  = json.dumps(latest,   indent=2, sort_keys=True).splitlines()
            diff = "\n".join(difflib.unified_diff(prev_lines, new_lines, lineterm=""))
        else:
            diff = "No previous snapshot existed; this is the first run."

        email_update(diff, "API Update Detected")
        save_latest_json(latest, JSON_FILE)
    else:
        print("No change detected in the JSON.")

    latest = fetch_latest_html()
    previous = load_previous_html()

    if previous != latest:
        # Build a human-readable diff for the e-mail body
        diff = ""
        if previous is not None:
            diff = "\n".join(
                difflib.unified_diff(
                    previous.splitlines(),
                    latest.splitlines(),
                    fromfile="old",
                    tofile="new",
                    lineterm="",
                ))
        else:
            diff = "No previous snapshot existed; this is the first run."

        email_update(diff, "HTML Update Detected")
        save_latest_html(latest, HTML_FILE)
    else:
        print("No change detected in the HTML.")


if __name__ == "__main__":
    main()
