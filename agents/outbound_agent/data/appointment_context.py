"""Appointment backfill campaign context data loader."""

import logging
import sys
import os

# Ensure we can import from project root 'utils'
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, "../../.."))

if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Fallback: try one level deeper if 'agents' is root
agent_root = os.path.abspath(os.path.join(current_dir, "../.."))
if agent_root not in sys.path:
    sys.path.insert(0, agent_root)

from utils.db import get_db_connection


def _get_appointment_data(phone_number: str, patient_id: str = None):
    """Fetch appointment backfill context from DB.
    
    Args:
        phone_number: Patient's phone number
        patient_id: Optional patient ID for strict matching
        
    Returns:
        dict: Appointment context data or None if not found
        {
            "patient_id": "PAT001",
            "patient_first_name": "Mark",
            "patient_last_name": "Reynolds",
            "patient_email": "mark.reynolds@email.com",
            "clinic_name": "Northview Family Medicine",
            "provider_name": "Dr. Sarah Patel",
            "original_date": "2026-02-03",
            "original_time": "10:00 AM",
            "available_date": "2026-02-01",
            "available_time": "2:30 PM",
            "phone_number": "9135960926",
            "appointment_id": "APPT001"
        }
    """
    conn = get_db_connection()
    if not conn:
        return None
    try:
        cur = conn.cursor()
        
        # Query joins backfill queue with patient, appointment, provider, and clinic info
        if patient_id:
            query = """
                SELECT 
                    p.patient_id, p.first_name, p.last_name, p.email, p.phone_number,
                    c.clinic_name, pr.provider_name,
                    a.appointment_date, a.appointment_time, a.appointment_id,
                    bq.available_slot_date, bq.available_slot_time
                FROM appointment_backfill_queue bq
                JOIN patients p ON bq.patient_id = p.patient_id
                JOIN appointments a ON bq.original_appointment_id = a.appointment_id
                JOIN providers pr ON bq.provider_id = pr.provider_id
                JOIN clinics c ON pr.clinic_id = c.clinic_id
                WHERE p.phone_number = %s AND p.patient_id = %s AND bq.call_status = 'Not Called'
                LIMIT 1
            """
            params = (phone_number, patient_id)
        else:
            # Fallback for legacy calls
            logging.warning("Loose appointment lookup (missing patient_id)")
            query = """
                SELECT 
                    p.patient_id, p.first_name, p.last_name, p.email, p.phone_number,
                    c.clinic_name, pr.provider_name,
                    a.appointment_date, a.appointment_time, a.appointment_id,
                    bq.available_slot_date, bq.available_slot_time
                FROM appointment_backfill_queue bq
                JOIN patients p ON bq.patient_id = p.patient_id
                JOIN appointments a ON bq.original_appointment_id = a.appointment_id
                JOIN providers pr ON bq.provider_id = pr.provider_id
                JOIN clinics c ON pr.clinic_id = c.clinic_id
                WHERE p.phone_number = %s AND bq.call_status = 'Not Called'
                LIMIT 1
            """
            params = (phone_number,)

        cur.execute(query, params)
        result = cur.fetchone()
        
        if result:
            patient_id, first_name, last_name, email, phone, \
            clinic_name, provider_name, \
            orig_date, orig_time, appt_id, \
            avail_date, avail_time = result
            
            # Format times for conversation (HH:MM AM/PM)
            orig_time_str = orig_time.strftime("%-I:%M %p") if orig_time else "10:00 AM"
            avail_time_str = avail_time.strftime("%-I:%M %p") if avail_time else "2:30 PM"
            
            return {
                "patient_id": patient_id,
                "patient_first_name": first_name,
                "patient_last_name": last_name,
                "patient_name": f"{first_name} {last_name}",
                "patient_email": email,
                "phone_number": phone,
                "clinic_name": clinic_name,
                "provider_name": provider_name,
                "original_date": str(orig_date),
                "original_time": orig_time_str,
                "available_date": str(avail_date),
                "available_time": avail_time_str,
                "appointment_id": appt_id
            }
        return None
    except Exception as e:
        logging.error(f"DB Appointment Lookup Error: {e}")
        return None
    finally:
        if conn:
            conn.close()
