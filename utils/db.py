import os
import logging
import psycopg2

# Defaults provided for safety, but should be set in environment.
DB_HOST = os.environ.get("DB_HOST", "localhost")
DB_NAME = os.environ.get("DB_NAME", "outbound_agent_db")
DB_USER = os.environ.get("DB_USER", "user")
DB_PASS = os.environ.get("DB_PASSWORD", "password")

def get_db_connection():
    """Establishes a connection to the PostgreSQL database."""
    try:
        conn = psycopg2.connect(
            host=DB_HOST,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASS
        )
        return conn
    except Exception as e:
        logging.error(f"Failed to connect to DB: {e}")
        return None
