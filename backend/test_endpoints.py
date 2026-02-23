import requests
import time
import sys
import json

BASE_URL = "http://localhost:8001"

def print_result(name, success, details=""):
    status = "✅ PASS" if success else "❌ FAIL"
    print(f"{status} - {name}")
    if not success and details:
        print(f"   Details: {details}")

def test_health():
    try:
        resp = requests.get(f"{BASE_URL}/health")
        if resp.status_code == 200:
            print_result("Health Check", True)
            return True
        else:
            print_result("Health Check", False, f"Status: {resp.status_code}")
            return False
    except Exception as e:
        print_result("Health Check", False, str(e))
        return False

def test_chat_flow():
    # 1. Start a new chat
    print("\n--- Testing Chat Flow ---")
    payload = {
        "question": "Test question one",
        "user_id": "test_user_1",
        # No conversation_id, should create one
    }
    
    try:
        resp = requests.post(f"{BASE_URL}/api/chat/query", json=payload)
        if resp.status_code != 200:
            print_result("Chat Query (New Session)", False, f"Status: {resp.status_code}, Body: {resp.text}")
            return
        
        data = resp.json()
        if not data.get("success"):
            print_result("Chat Query (New Session)", False, "Success flag is False")
            return
            
        conv_id = data.get("conversation_id")
        print_result("Chat Query (New Session)", True, f"Created ID: {conv_id}")
        
        # 2. Follow up (Short Term Memory Check)
        payload2 = {
            "question": "Test question two",
            "user_id": "test_user_1",
            "conversation_id": conv_id
        }
        resp2 = requests.post(f"{BASE_URL}/api/chat/query", json=payload2)
        if resp2.status_code == 200:
             print_result("Chat Query (Follow Up)", True)
        else:
             print_result("Chat Query (Follow Up)", False, resp2.text)

        # 3. Check History
        resp_hist = requests.get(f"{BASE_URL}/api/chat/history/{conv_id}")
        if resp_hist.status_code == 200:
            hist_data = resp_hist.json()
            msgs = hist_data.get("messages", [])
            # Should have 4 messages (User, AI, User, AI)
            if len(msgs) >= 4:
                print_result("Chat History", True, f"Count: {len(msgs)}")
            else:
                print_result("Chat History", False, f"Expected 4+, got {len(msgs)}")
        else:
            print_result("Chat History", False, resp_hist.text)

        # 4. Check Sessions
        resp_sess = requests.get(f"{BASE_URL}/api/chat/sessions")
        if resp_sess.status_code == 200:
            sess_data = resp_sess.json()
            sessions = sess_data.get("sessions", [])
            # Verify our conv_id is in there
            found = any(s["id"] == conv_id for s in sessions)
            if found:
                print_result("Chat Sessions List", True)
            else:
                 print_result("Chat Sessions List", False, f"ID {conv_id} not found in sessions")
        else:
            print_result("Chat Sessions List", False, resp_sess.text)

        # 5. Clear History
        resp_del = requests.delete(f"{BASE_URL}/api/chat/history/{conv_id}")
        if resp_del.status_code == 200 and resp_del.json().get("success"):
             print_result("Clear History", True)
        else:
             print_result("Clear History", False, resp_del.text)

        # 6. Verify Gone
        resp_gone = requests.get(f"{BASE_URL}/api/chat/history/{conv_id}")
        if resp_gone.json().get("success") is False:
             print_result("Verify History Cleared", True)
        else:
             print_result("Verify History Cleared", False, "History still exists")

    except Exception as e:
        print_result("Chat Flow Exception", False, str(e))

def test_transcribe_endpoint():
    print("\n--- Testing Transcribe ---")
    # Expect 422 if no file sent
    resp = requests.post(f"{BASE_URL}/api/chat/transcribe")
    if resp.status_code == 422:
        print_result("Transcribe (Validation)", True, "Got expected 422 for missing file")
    else:
        print_result("Transcribe (Validation)", False, f"Expected 422, got {resp.status_code}")

if __name__ == "__main__":
    print("Waiting for server...")
    # diverse attempts to connect
    for _ in range(10):
        try:
            if test_health():
                break
        except:
            pass
        time.sleep(1)
    else:
        print("Server not available.")
        sys.exit(1)
        
    test_chat_flow()
    test_transcribe_endpoint()
