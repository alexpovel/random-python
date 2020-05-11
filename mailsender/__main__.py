import json
from importlib.resources import open_text
from smtplib import SMTP_SSL

with open_text("mailsender", "email_config.json") as email_file, open_text(
    "mailsender", "user_config.json"
) as user_file:
    email_config = json.load(email_file)
    user_config = json.load(user_file)

message = f"""\
Subject: {email_config["subject"]}

{email_config["message"]}
"""

with SMTP_SSL(user_config["smtp_server"]) as smtp_connection:
    smtp_connection.login(user_config["username"], user_config["password"])
    smtp_connection.sendmail(
        user_config["from_address"], user_config["to_address"], message
    )
