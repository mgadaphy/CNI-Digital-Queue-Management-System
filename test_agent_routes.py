#!/usr/bin/env python3
"""
Test Agent Routes - Verify agent status and call next routes are working
"""

import os
import sys
import requests
import json

def test_agent_routes():
    """Test agent routes with actual HTTP requests"""
    
    base_url = "http://127.0.0.1:5000"
    
    print("🧪 Testing Agent Routes")
    print("=" * 40)
    
    # Test 1: Check if agent status route exists
    print("1. Testing agent status route...")
    try:
        response = requests.put(f"{base_url}/agent/api/status", 
                              json={"status": "available"},
                              headers={"Content-Type": "application/json"})
        print(f"   Status Code: {response.status_code}")
        if response.status_code == 401:
            print("   ✅ Route exists (401 = needs authentication)")
        elif response.status_code == 404:
            print("   ❌ Route not found (404)")
        else:
            print(f"   Response: {response.text[:100]}...")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    # Test 2: Check if call next route exists
    print("\n2. Testing call next citizen route...")
    try:
        response = requests.get(f"{base_url}/agent/api/queue/next",
                              headers={"Content-Type": "application/json"})
        print(f"   Status Code: {response.status_code}")
        if response.status_code == 401:
            print("   ✅ Route exists (401 = needs authentication)")
        elif response.status_code == 404:
            print("   ❌ Route not found (404)")
        else:
            print(f"   Response: {response.text[:100]}...")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    # Test 3: Check agent dashboard route
    print("\n3. Testing agent dashboard route...")
    try:
        response = requests.get(f"{base_url}/agent/dashboard")
        print(f"   Status Code: {response.status_code}")
        if response.status_code in [200, 302, 401]:
            print("   ✅ Route exists")
        elif response.status_code == 404:
            print("   ❌ Route not found (404)")
        else:
            print(f"   Response: {response.text[:100]}...")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    print("\n🎯 Summary:")
    print("If routes show 401 (Unauthorized), they exist but need login")
    print("If routes show 404 (Not Found), there's a routing problem")
    print("Make sure the Flask server is running on http://127.0.0.1:5000")

if __name__ == '__main__':
    test_agent_routes()
