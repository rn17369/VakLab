#!/usr/bin/env python3
"""
Complete test workflow for VakLab
Tests both HEDIS and Appointment campaigns
"""
import requests
import json
import time
import sys

BASE_URL = "http://localhost:8000"

def print_section(title):
    print("\n" + "="*60)
    print(f"  {title}")
    print("="*60 + "\n")

def test_health():
    """Test health endpoint"""
    print_section("Step 1: Health Check")
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        if response.status_code == 200:
            print("✅ Server is healthy")
            return True
        else:
            print(f"❌ Health check failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Server not responding: {e}")
        print("   Make sure server is running: ./start.sh")
        return False

def check_database():
    """Check database records"""
    print_section("Step 2: Database Check")
    print("Checking campaign_target_member_call_list...")
    print("(This requires direct DB access)")
    print("")
    print("Run this to check:")
    print("  docker exec -it outbound_agent_db psql -U user -d outbound_agent_db -c")
    print("  \"SELECT member_id, phone_number, campaign_name, call_status FROM campaign_target_member_call_list;\"")
    print("")
    input("Press Enter when ready to continue...")

def test_outbound_call(campaign_name="HEDIS"):
    """Trigger an outbound call"""
    print_section(f"Step 3: Trigger {campaign_name} Call")
    
    try:
        print("📞 Calling /twilio/outbound-call endpoint...")
        response = requests.post(f"{BASE_URL}/twilio/outbound-call", timeout=10)
        
        print(f"\nResponse Status: {response.status_code}")
        print(f"Response Body:\n{json.dumps(response.json(), indent=2)}")
        
        if response.status_code == 200:
            result = response.json()
            if result.get("status") == "queued":
                print("\n✅ Call queued successfully!")
                print(f"   Call SID: {result.get('call_sid')}")
                print(f"   Member ID: {result.get('member_id')}")
                print(f"   Campaign: {result.get('campaign')}")
                
                print("\n📱 Your phone should ring soon...")
                print("   Answer the call and interact with the agent")
                
                return result.get('call_sid')
            elif result.get("status") == "info":
                print(f"\nℹ️  Info: {result.get('message')}")
                return None
            else:
                print("\n⚠️  Unexpected response")
                return None
        else:
            print(f"\n❌ Call failed with status {response.status_code}")
            return None
            
    except Exception as e:
        print(f"\n❌ Error: {e}")
        return None

def monitor_call(call_sid):
    """Instructions for monitoring the call"""
    if not call_sid:
        return
    
    print_section("Step 4: Monitor the Call")
    print("While the call is active, you can:")
    print("")
    print("1. Watch server logs in the terminal running uvicorn")
    print("   Look for:")
    print("   - [EVENT] Pipecat bot connected")
    print("   - [GREETING] Triggered LLM to generate greeting")
    print("   - [TOOL] Tool invocations")
    print("")
    print("2. Check Twilio console:")
    print(f"   https://console.twilio.com/monitor/logs/calls/{call_sid}")
    print("")
    print("3. Answer the phone and have a conversation!")
    print("")
    input("Press Enter after the call completes...")

def download_recording():
    """Download the recording"""
    print_section("Step 5: Download Recording")
    
    print("🎙️  Downloading call recording...")
    print("")
    
    try:
        import subprocess
        result = subprocess.run(
            ["python", "download_recording.py"],
            capture_output=True,
            text=True
        )
        
        print(result.stdout)
        if result.returncode == 0:
            print("\n✅ Recording downloaded successfully!")
            print("   Check for .mp3 files in current directory")
        else:
            print("\n⚠️  Recording download failed or no recordings found")
            print("   Note: Recordings may take a minute to be available")
            
    except Exception as e:
        print(f"❌ Error: {e}")

def main():
    print("""
╔══════════════════════════════════════════════════════════╗
║                                                          ║
║               VakLab Complete Test Suite                ║
║                                                          ║
╚══════════════════════════════════════════════════════════╝
    """)
    
    # Step 1: Health check
    if not test_health():
        sys.exit(1)
    
    # Step 2: Database check
    check_database()
    
    # Step 3: Trigger call
    call_sid = test_outbound_call()
    
    # Step 4: Monitor
    monitor_call(call_sid)
    
    # Step 5: Download recording
    if call_sid:
        download_recording()
    
    # Summary
    print_section("Complete!")
    print("✅ Test workflow finished")
    print("")
    print("Next steps:")
    print("1. Review the call recording (*.mp3)")
    print("2. Check server logs for any errors")
    print("3. Verify database was updated")
    print("4. Try different test scenarios")
    print("")
    print("For appointment campaign, update database:")
    print("""
    docker exec -it outbound_agent_db psql -U user -d outbound_agent_db -c 
    "UPDATE campaign_target_member_call_list 
     SET campaign_name='appointment_backfill', call_status='Not Called'
     WHERE member_id='1001';"
    """)

if __name__ == "__main__":
    main()
