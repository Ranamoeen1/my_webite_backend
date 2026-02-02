
import requests
import time
import json
import os

API_URL = "http://localhost:7860/api/download"

TEST_URLS = [
    # YouTube (Me at the zoo - usually safe)
    {"platform": "YouTube Public", "url": "https://www.youtube.com/watch?v=jNQXAC9IVRw"},
    # Instagram Reel (Public)
    # User Reported Video
    {"platform": "User Test Case", "url": "https://youtu.be/KUpwupYj_tY?si=q8m9ih6x1L0nzyFG"},
    # Geo-Restricted (Blocked in US, available in CA/UK etc.) 
    # Facebook Video
    {"platform": "Facebook", "url": "https://www.facebook.com/watch/?v=10153231379946729"}, 
    # Geo-Restricted (Blocked in US, available in CA/UK etc.)
    {"platform": "Geo-Restricted Test", "url": "https://www.youtube.com/watch?v=z23GK9PO2jE"},
]

def test_download(test_case):
    print(f"\n--- Testing {test_case['platform']} ---")
    print(f"URL: {test_case['url']}")
    
    start_time = time.time()
    try:
        response = requests.post(API_URL, json={"url": test_case['url'], "quality": "best"})
        duration = time.time() - start_time
        
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                print(f"✅ SUCCESS ({duration:.2f}s)")
                print(f"   Title: {data.get('title')}")
                print(f"   File: {data.get('filename')}")
                print(f"   Size: {data.get('file_size')} bytes")
                # Verify file actually exists locally for the server
                # (Since we are running script on same machine as server, we can check 'downloads' folder if we know where it is relative)
            else:
                print(f"❌ FAILED (API returned success=False)")
                print(f"   Error: {data.get('error')}")
        else:
            print(f"❌ FAILED (HTTP {response.status_code})")
            try:
                print(f"   Error: {response.json().get('error')}")
            except:
                print(f"   Response: {response.text[:200]}")
                
    except Exception as e:
        print(f"❌ ERROR: {e}")

if __name__ == "__main__":
    print("Starting Verification...")
    # Health check
    try:
        r = requests.get("http://localhost:7860/api/health")
        print(f"Server Status: {r.status_code} {r.json()}")
    except Exception as e:
        print(f"Server not running? {e}")
        exit(1)
        
    for test in TEST_URLS:
        test_download(test)
