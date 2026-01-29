"""Appointment backfill campaign tools."""

import os
import logging
import sys

# Ensure we can import from project root 'utils'
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, "../../.."))

if project_root not in sys.path:
    sys.path.insert(0, project_root)

from utils.db import get_db_connection


def reschedule_appointment(patient_id: str, new_date: str, new_time: str):
    """Updates appointment in DB to new slot and marks backfill as processed.
    
    Args:
        patient_id: Patient ID
        new_date: New appointment date (YYYY-MM-DD)
        new_time: New appointment time (HH:MM:SS or HH:MM AM/PM)
        
    Returns:
        bool: True if successful, False otherwise
    """
    conn = get_db_connection()
    if not conn:
        logging.error("Database connection failed")
        return False
    
    try:
        cur = conn.cursor()
        
        # Parse time if it's in AM/PM format
        if "AM" in new_time or "PM" in new_time:
            from datetime import datetime
            time_obj = datetime.strptime(new_time, "%I:%M %p")
            new_time = time_obj.strftime("%H:%M:%S")
        
        # Update appointment date and time
        cur.execute("""
            UPDATE appointments
            SET appointment_date = %s, appointment_time = %s, status = 'rescheduled'
            WHERE patient_id = %s
            RETURNING appointment_id
        """, (new_date, new_time, patient_id))
        
        result = cur.fetchone()
        if not result:
            logging.error(f"No appointment found for patient {patient_id}")
            conn.rollback()
            return False
        
        # Mark backfill queue entry as processed
        cur.execute("""
            UPDATE appointment_backfill_queue
            SET call_status = 'Called - Rescheduled'
            WHERE patient_id = %s
        """, (patient_id,))
        
        conn.commit()
        logging.info(f"✓ Rescheduled appointment for {patient_id} to {new_date} {new_time}")
        return True
        
    except Exception as e:
        logging.error(f"Failed to reschedule appointment: {e}")
        if conn:
            conn.rollback()
        return False
    finally:
        if conn:
            conn.close()


def send_confirmation_sms(phone_number: str, message: str):
    """Sends SMS confirmation via Twilio.
    
    Args:
        phone_number: Patient phone number (e.g. '9135960926')
        message: SMS message content
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        from twilio.rest import Client
        from dotenv import load_dotenv
        load_dotenv(override=True)
        
        # Get Twilio credentials
        account_sid = os.getenv("TWILIO_SID")
        auth_token = os.getenv("TWILIO_AUTH")
        twilio_number = os.getenv("TWILIO_NUMBER")
        
        if not all([account_sid, auth_token, twilio_number]):
            logging.error("Twilio credentials not configured")
            return False
        
        # Format phone number (add +1 if not present)
        if not phone_number.startswith('+'):
            phone_number = f"+1{phone_number}"
        
        # Send SMS
        client = Client(account_sid, auth_token)
        sms = client.messages.create(
            body=message,
            from_=twilio_number,
            to=phone_number
        )
        
        logging.info(f"✓ SMS sent to {phone_number}: {sms.sid}")
        return True
        
    except Exception as e:
        logging.error(f"Failed to send SMS to {phone_number}: {e}")
        return False
