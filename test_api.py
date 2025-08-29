#!/usr/bin/env python3
"""
Simple API test script for YouTube Music Channel Automation Platform
"""

import requests
import json
import time

BASE_URL = "http://localhost:8000"

def test_health():
    """Test health endpoint"""
    print("🔍 Testing health endpoint...")
    try:
        response = requests.get(f"{BASE_URL}/api/health")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Health check passed: {data['status']}")
            print(f"   Checks: {data['checks']}")
            return True
        else:
            print(f"❌ Health check failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Health check error: {e}")
        return False

def test_projects():
    """Test projects endpoints"""
    print("\n📁 Testing projects endpoints...")
    
    # Get all projects
    try:
        response = requests.get(f"{BASE_URL}/api/projects")
        if response.status_code == 200:
            projects = response.json()
            print(f"✅ Retrieved {len(projects)} projects")
        else:
            print(f"❌ Failed to get projects: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Error getting projects: {e}")
        return False
    
    # Create a test project
    test_project = {"name": f"Test Project {int(time.time())}"}
    try:
        response = requests.post(
            f"{BASE_URL}/api/projects",
            json=test_project,
            headers={"Content-Type": "application/json"}
        )
        if response.status_code == 200:
            created_project = response.json()
            project_id = created_project['id']
            print(f"✅ Created test project: {created_project['name']} (ID: {project_id})")
            
            # Test getting the specific project
            response = requests.get(f"{BASE_URL}/api/projects/{project_id}")
            if response.status_code == 200:
                print(f"✅ Retrieved project details")
            else:
                print(f"❌ Failed to get project details: {response.status_code}")
            
            # Test updating the project
            update_data = {"name": f"Updated {test_project['name']}"}
            response = requests.put(
                f"{BASE_URL}/api/projects/{project_id}",
                json=update_data,
                headers={"Content-Type": "application/json"}
            )
            if response.status_code == 200:
                print(f"✅ Updated project name")
            else:
                print(f"❌ Failed to update project: {response.status_code}")
            
            # Test deleting the project
            response = requests.delete(f"{BASE_URL}/api/projects/{project_id}")
            if response.status_code == 200:
                print(f"✅ Deleted test project")
            else:
                print(f"❌ Failed to delete project: {response.status_code}")
            
            return True
        else:
            print(f"❌ Failed to create project: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Error creating project: {e}")
        return False

def test_api_info():
    """Test API info endpoint"""
    print("\n📚 Testing API info endpoint...")
    try:
        response = requests.get(f"{BASE_URL}/api")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ API info: {data['name']} v{data['version']}")
            return True
        else:
            print(f"❌ Failed to get API info: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Error getting API info: {e}")
        return False

def main():
    """Run all tests"""
    print("🧪 YouTube Music Channel Automation Platform - API Tests")
    print("=" * 60)
    
    tests = [
        test_health,
        test_api_info,
        test_projects,
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            if test():
                passed += 1
        except Exception as e:
            print(f"❌ Test {test.__name__} crashed: {e}")
    
    print("\n" + "=" * 60)
    print(f"📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! The API is working correctly.")
    else:
        print("⚠️  Some tests failed. Check the logs above for details.")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
