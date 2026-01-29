"""HEDIS campaign specific tools."""

import os
import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage


def send_enrollment_email(email_address, first_name):
    """
    Sends a beautifully formatted HTML welcome email for the 
    Metna Better Care Rewards program using inline images.
    """
    subject = f"For you, and everyone who counts on you, {first_name}"
    
    # 1. HTML Content with dynamic first_name
    html_content = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="margin: 0; padding: 0; background-color: #f4f4f4; font-family: Arial, sans-serif;">
    <table border="0" cellpadding="0" cellspacing="0" width="100%">
        <tr>
            <td align="center" style="padding: 20px 0;">
                <table border="0" cellpadding="0" cellspacing="0" width="600" style="background-color: #ffffff; border-radius: 8px; overflow: hidden; border: 1px solid #dddddd;">
                    
                    <tr>
                        <td align="center" style="padding: 20px;">
                            <img src="cid:logo" alt="Metna" width="140" style="display: block; border: 0;">
                            <p style="font-size: 12px; color: #666666; margin-top: 5px;">Health and wellness or prevention information</p>
                        </td>
                    </tr>

                    <tr>
                        <td align="center" style="padding: 0 20px;">
                            <img src="cid:hero_image" alt="Live Well with Metna" width="560" style="display: block; width: 100%; max-width: 560px; border-radius: 15px;">
                        </td>
                    </tr>

                    <tr>
                        <td style="padding: 30px 40px; color: #333333; line-height: 1.6;">
                            <h1 style="color: #4A2D82; font-size: 24px; margin-bottom: 10px;">Dear {first_name},</h1>
                            <p style="font-size: 16px;">
                                You're the glue that holds your circle together—and at <b>Metna</b>, that's why your health matters most to us.
                            </p>
                            <p style="font-size: 16px;">
                                Knowing where you stand when it comes to breast cancer means peace of mind for you and everyone who counts on you.
                            </p>
                        </td>
                    </tr>

                    <tr>
                        <td align="center" style="padding: 40px; background-color: #4A2D82; color: #ffffff;">
                            <h2 style="margin: 0; font-size: 22px;">Make the call.</h2>
                            <p style="font-size: 16px; margin: 10px 0 20px 0;">Your mammogram is covered by your <b>Metna Medicare plan</b>.</p>
                            <div style="background-color: #ffffff; color: #4A2D82; padding: 15px 25px; border-radius: 5px; font-weight: bold; display: inline-block;">
                                CALL 1-833-998-2287
                            </div>
                        </td>
                    </tr>
                </table>
            </td>
        </tr>
    </table>
</body>
</html>"""
    
    # 2. Logic to interface with SMTP
    from dotenv import load_dotenv
    load_dotenv(override=True)
    
    smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
    smtp_port = int(os.getenv("SMTP_PORT", 587))
    smtp_user = os.getenv("SMTP_USER")
    smtp_password = os.getenv("SMTP_PASSWORD")
    
    if not smtp_user or not smtp_password:
        logging.error("SMTP credentials not configured")
        return False
    
    try:
        # Create the 'related' message to allow for inline images
        msg = MIMEMultipart("related")
        msg["Subject"] = subject
        msg["From"] = smtp_user
        msg["To"] = email_address
        
        # Attach HTML
        msg.attach(MIMEText(html_content, "html"))
        
        # 3. Attach the Images
        # Note: Ensure 'mjon.jpg' and 'metna_logo.png' are in your script's folder
        image_files = [
            ("metna_logo.png", "logo"),     # Your logo file
            ("mjon.jpg", "hero_image")      # The heart-shaped hero image
        ]

        for file_path, cid in image_files:
            if os.path.exists(file_path):
                with open(file_path, "rb") as f:
                    img = MIMEImage(f.read())
                    img.add_header("Content-ID", f"<{cid}>")
                    msg.attach(img)
            else:
                logging.warning(f"Image file {file_path} not found. Email will send without it.")

        # 4. Send the email
        logging.info(f"Connecting to SMTP server {smtp_server}:{smtp_port}...")
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(smtp_user, smtp_password)
            server.sendmail(smtp_user, email_address, msg.as_string())
        
        logging.info(f"✓ Email successfully sent to {email_address} for {first_name}")
        return True
        
    except Exception as e:
        logging.error(f"Failed to send email to {email_address}: {e}")
        return False
