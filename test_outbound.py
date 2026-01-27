#!/usr/bin/env python3
"""
Test script for the outbound calling system
"""
import requests
import json
import sys

# Configuration
BASE_URL = "http://localhost:8000"  # Change if your server runs on a different port
OUTBOUND_ENDPOINT = f"{BASE_URL}/twilio/outbound-call"

def test_outbound_call():
    """Test the outbound call endpoint"""
    print("=" * 60)
    print("Testing Outbound Call System")
    print("=" * 60)
    
    try:
        # Make the POST request
        print(f"\n📞 Calling endpoint: {OUTBOUND_ENDPOINT}")
        response = requests.post(OUTBOUND_ENDPOINT, timeout=10)
        
        # Display results
        print(f"\n✓ Response Status: {response.status_code}")
        print(f"✓ Response Body:")
        print(json.dumps(response.json(), indent=2))
        
        # Check the response
        if response.status_code == 200:
            result = response.json()
            if result.get("status") == "queued":
                print("\n✅ SUCCESS! Call has been queued")
                print(f"   Call SID: {result.get('call_sid')}")
                print(f"   Member ID: {result.get('member_id')}")
                print(f"   Campaign: {result.get('campaign')}")
            elif result.get("status") == "info":
                print(f"\nℹ️  INFO: {result.get('message')}")
            else:
                print("\n⚠️  Unexpected response format")
        else:
            print(f"\n❌ FAILED with status {response.status_code}")
            
    except requests.exceptions.ConnectionError:
        print("\n❌ ERROR: Could not connect to the server")
        print("   Make sure the server is running on", BASE_URL)
        print("   Start it with: uvicorn main:app --reload")
        sys.exit(1)
    except requests.exceptions.Timeout:
        print("\n❌ ERROR: Request timed out")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}")
        sys.exit(1)

def test_health_check():
    """Test the health check endpoint"""
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        if response.status_code == 200:
            print("✅ Health check passed")
            return True
        else:
            print(f"⚠️  Health check returned status {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Health check failed: {e}")
        return False

if __name__ == "__main__":
    print("\n🔍 Step 1: Checking server health...")
    if test_health_check():
        print("\n🔍 Step 2: Testing outbound call...")
        test_outbound_call()
    else:
        print("\n❌ Server is not responding. Please start the server first.")
        print("   Run: uvicorn main:app --reload")
