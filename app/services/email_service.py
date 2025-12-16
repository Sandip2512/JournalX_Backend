import os
from dotenv import load_dotenv
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

# Load environment variables
load_dotenv()

def send_reset_email(to_email: str, reset_link: str):
    message = Mail(
        from_email="theempire662@gmail.com",  # must be verified in SendGrid
        to_emails=to_email,
        subject="🔑 Password Reset Request - The Empire",
        html_content=f"""
        <html>
            <body style="font-family: Arial, sans-serif; background-color: #f4f4f4; padding: 20px;">
                <div style="max-width: 600px; margin: auto; background: #ffffff; padding: 20px; border-radius: 10px; text-align: center; box-shadow: 0 2px 8px rgba(0,0,0,0.1);">
                    
                    <!-- Company Logo -->
                    <img src="http://cdn.mcauto-images-production.sendgrid.net/8adc41f77da7c0ea/8439574e-e6ef-463d-a2d9-7e771a24d595/1024x1024.jpeg" 
                         alt="The Empire Logo" style="width:120px; margin-bottom: 20px;" />
                    
                    <h2 style="color: #333;">Password Reset Request</h2>
                    <p style="color: #555; font-size: 15px;">
                        We received a request to reset your password.  
                        Click the button below to reset it:
                    </p>
                    
                    <!-- Reset Button -->
                    <a href="{reset_link}" 
                       style="display:inline-block; background-color:#007bff; color:#fff; padding:12px 20px; text-decoration:none; border-radius:5px; margin-top:20px; font-size:16px;">
                        🔑 Reset Password
                    </a>
                    
                    <p style="color:#999; font-size:12px; margin-top:30px;">
                        If you did not request this, you can safely ignore this email.
                    </p>
                </div>
            </body>
        </html>
        """
    )
    try:
        sg = SendGridAPIClient(os.getenv("SENDGRID_API_KEY"))
        response = sg.send(message)
        print(f"✅ Email sent: {response.status_code}")
    except Exception as e:
        print(f"❌ Email sending failed: {str(e)}")
