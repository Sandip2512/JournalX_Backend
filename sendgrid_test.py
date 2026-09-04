import os
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

api_key = os.getenv("SENDGRID_API_KEY")
print("API Key Loaded:", bool(api_key))  # check if .env key is found

message = Mail(
    from_email="theempire662@gmail.com",  # must be verified in SendGrid
    to_emails="salunkhesandip2512@gmail.com",         # where you want to receive
    subject="✅ SendGrid Test Email",
    html_content="<strong>Hello, this is a test email from your Trading App!</strong>"
)

try:
    sg = SendGridAPIClient(api_key)
    response = sg.send(message)
    print("STATUS:", response.status_code)
    print("BODY:", response.body)
    print("HEADERS:", response.headers)
except Exception as e:
    print("ERROR:", str(e))
