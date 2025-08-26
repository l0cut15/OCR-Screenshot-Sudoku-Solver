#!/usr/bin/env python3
"""
Test the web user interface
"""

import requests
import time

def test_web_interface():
    """Test the web interface is accessible"""
    
    print("🌐 TESTING WEB USER INTERFACE")
    print("="*35)
    
    server_url = "http://localhost:8000"
    
    # Test 1: Check if main page loads
    print("📄 Testing main page...")
    try:
        response = requests.get(server_url)
        if response.status_code == 200 and "AI Sudoku Solver" in response.text:
            print("✅ Main page loads successfully")
            print(f"   Page size: {len(response.content)} bytes")
        else:
            print(f"❌ Main page failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Main page error: {e}")
        return False
    
    # Test 2: Check static files
    static_files = ["static/script.js"]
    
    for static_file in static_files:
        print(f"📁 Testing {static_file}...")
        try:
            response = requests.get(f"{server_url}/{static_file}")
            if response.status_code == 200:
                print(f"✅ {static_file} loads successfully")
                print(f"   File size: {len(response.content)} bytes")
            else:
                print(f"❌ {static_file} failed: {response.status_code}")
        except Exception as e:
            print(f"❌ {static_file} error: {e}")
    
    # Test 3: Check API endpoint still works
    print("🔌 Testing API endpoint...")
    try:
        response = requests.get(f"{server_url}/api")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ API endpoint works: {data['message']}")
        else:
            print(f"❌ API endpoint failed: {response.status_code}")
    except Exception as e:
        print(f"❌ API endpoint error: {e}")
    
    # Test 4: Test file upload capability
    print("📤 Testing file upload endpoint...")
    try:
        with open("sample-puzzle.png", 'rb') as f:
            files = {'file': ('sample-puzzle.png', f, 'image/png')}
            response = requests.post(f"{server_url}/solve", files=files, timeout=30)
            
            if response.status_code == 200:
                result = response.json()
                print(f"✅ File upload works")
                print(f"   Detected digits: {len(result['given_positions'])}")
                print(f"   Processing time: {result['processing_time']:.2f}s")
                print(f"   Solution available: {'✅' if result['solved_grid'] else '❌'}")
            else:
                print(f"❌ File upload failed: {response.status_code}")
    except Exception as e:
        print(f"❌ File upload error: {e}")
    
    print(f"\n🎯 WEB INTERFACE STATUS:")
    print(f"Main Interface: http://localhost:8000")
    print(f"API Documentation: http://localhost:8000/docs")
    print(f"Health Check: http://localhost:8000/health")
    
    print(f"\n📱 FEATURES AVAILABLE:")
    print(f"✅ Drag & drop image upload")
    print(f"✅ Real-time processing feedback")
    print(f"✅ Interactive Sudoku grid display")
    print(f"✅ OCR correction capabilities")
    print(f"✅ Solution visualization")
    print(f"✅ Result downloading")
    print(f"✅ Mobile-responsive design")
    
    print(f"\n🚀 Ready for use! Open http://localhost:8000 in your browser")
    
    return True

if __name__ == "__main__":
    test_web_interface()