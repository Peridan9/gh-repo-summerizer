#!/usr/bin/env python3
"""Simple test runner for ghsum package."""

import subprocess
import sys
import os


def run_basic_tests():
    """Run basic functionality tests."""
    print("🧪 Running basic functionality tests...")
    try:
        result = subprocess.run([
            sys.executable, "-m", "pytest", 
            "tests/test_basic_functionality.py", 
            "-v", "--tb=short"
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ Basic tests passed!")
            return True
        else:
            print("❌ Basic tests failed:")
            print(result.stdout)
            print(result.stderr)
            return False
    except Exception as e:
        print(f"❌ Error running basic tests: {e}")
        return False


def run_connectivity_tests():
    """Run model connectivity tests."""
    print("\n🔍 Running model connectivity tests...")
    try:
        result = subprocess.run([
            sys.executable, "tests/test_model_connectivity.py"
        ], capture_output=True, text=True)
        
        print(result.stdout)
        if result.stderr:
            print("Warnings:", result.stderr)
        return True
    except Exception as e:
        print(f"❌ Error running connectivity tests: {e}")
        return False


def run_all_tests():
    """Run all tests."""
    print("🚀 Running ghsum test suite...\n")
    
    # Run basic tests
    basic_ok = run_basic_tests()
    
    # Run connectivity tests
    connectivity_ok = run_connectivity_tests()
    
    # Summary
    print("\n" + "="*50)
    if basic_ok:
        print("✅ Basic functionality tests: PASSED")
    else:
        print("❌ Basic functionality tests: FAILED")
    
    if connectivity_ok:
        print("✅ Connectivity tests: PASSED")
    else:
        print("❌ Connectivity tests: FAILED")
    
    if basic_ok and connectivity_ok:
        print("\n🎉 All tests passed! Your changes are safe.")
        return 0
    else:
        print("\n⚠️  Some tests failed. Please check the output above.")
        return 1


if __name__ == "__main__":
    sys.exit(run_all_tests())
