import os

# Check if running locally or through ngrok
domain = os.getenv("DOMAIN", "")
is_local = "localhost" in domain or "127.0.0.1" in domain