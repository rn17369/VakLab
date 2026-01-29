"""HEDIS campaign context data loader."""

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


def _get_member_data(phone_number: str, member_id: str = None, campaign_name: str = None):
    """Fetch member data from DB using strict matching.
    
    Args:
        phone_number: Patient's phone number
        member_id: Optional member ID for strict matching
        campaign_name: Optional campaign name for strict matching
        
    Returns:
        dict: Member context data or None if not found
    """
    conn = get_db_connection()
    if not conn:
        return None
    try:
        cur = conn.cursor()
        
        # Build query dynamically based on available filters
        if member_id and campaign_name:
            query = """
                SELECT member_id, member_first_name, member_last_name, member_email, 
                       campaign_name, zip_code, csr_name, csr_phone_number
                FROM target_members_detail
                WHERE phone_number = %s AND member_id = %s AND campaign_name = %s
            """
            params = (phone_number, member_id, campaign_name)
        else:
            # Fallback for legacy calls
            logging.warning("Loose lookup performed (missing member_id/campaign)")
            query = """
                SELECT member_id, member_first_name, member_last_name, member_email, 
                       campaign_name, zip_code, csr_name, csr_phone_number
                FROM target_members_detail
                WHERE phone_number = %s
            """
            params = (phone_number,)

        cur.execute(query, params)
        result = cur.fetchone()
        
        if result:
            member_id, member_first_name, member_last_name, member_email, \
            campaign_name, zip_code, csr_name, csr_phone_number = result
            return {
                "member_id": member_id,
                "member_first_name": member_first_name,
                "member_last_name": member_last_name,
                "member_name": f"{member_first_name} {member_last_name}",
                "member_email": member_email,
                "campaign_name": campaign_name,
                "zip_code": zip_code,
                "csr_name": csr_name,
                "csr_phone_number": csr_phone_number
            }
        return None
    except Exception as e:
        logging.error(f"DB Lookup Error: {e}")
        return None
    finally:
        if conn:
            conn.close()
