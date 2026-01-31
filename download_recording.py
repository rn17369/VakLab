#!/usr/bin/env python3
"""
Download most recent Twilio call recording
"""
import os
import sys
from twilio.rest import Client
from dotenv import load_dotenv
import requests
from datetime import datetime

load_dotenv()

# Check credentials
sid = os.getenv("TWILIO_SID")
auth = os.getenv("TWILIO_AUTH")

if not sid or not auth or sid == "your_twilio_account_sid":
    print("❌ Error: Twilio credentials not configured in .env")
    print("   Set TWILIO_SID and TWILIO_AUTH")
    sys.exit(1)

try:
    client = Client(sid, auth)
    
    # Get most recent call
    print("🔍 Fetching recent calls...")
    calls = client.calls.list(limit=5)
    
    if not calls:
        print("ℹ️  No calls found")
        sys.exit(0)
    
    print(f"\n📞 Found {len(calls)} recent calls:\n")
    
    for idx, call in enumerate(calls, 1):
        print(f"{idx}. Call SID: {call.sid}")
        print(f"   To: {call.to}")
        print(f"   From: {call.from_}")
        print(f"   Status: {call.status}")
        print(f"   Duration: {call.duration} seconds")
        print(f"   Date: {call.start_time}")
        
        # Get recordings for this call
        recordings = client.recordings.list(call_sid=call.sid)
        
        if recordings:
            print(f"   🎙️  Recordings: {len(recordings)}")
            for rec in recordings:
                print(f"      - Recording SID: {rec.sid}")
                print(f"        Duration: {rec.duration} seconds")
                
                # Download recording
                url = f"https://api.twilio.com/2010-04-01/Accounts/{sid}/Recordings/{rec.sid}.mp3"
                
                filename = f"recording_{call.sid}_{rec.sid}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp3"
                
                print(f"      ⬇️  Downloading to {filename}...")
                response = requests.get(url, auth=(sid, auth))
                
                if response.status_code == 200:
                    with open(filename, "wb") as f:
                        f.write(response.content)
                    print(f"      ✅ Saved!")
                else:
                    print(f"      ❌ Failed: HTTP {response.status_code}")
        else:
            print(f"   ⚠️  No recordings found")
        
        print()

except Exception as e:
    print(f"❌ Error: {e}")
    sys.exit(1)
