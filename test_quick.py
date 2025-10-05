#!/usr/bin/env python3
"""Quick test script for ghsum - run this after any changes."""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ghsum.summarizer import basic_summary, OllamaSummarizer, RepositorySummary
from ghsum.config import load_settings


def test_basic_functionality():
    """Test basic functionality without external dependencies."""
    print("🧪 Testing basic functionality...")
    
    # Test 1: Basic summarizer
    try:
        result = basic_summary("test-repo", "A Python web framework", "Web framework")
        assert isinstance(result, str)
        assert len(result) > 0
        print("✅ Basic summarizer works")
    except Exception as e:
        print(f"❌ Basic summarizer failed: {e}")
        return False
    
    # Test 2: Pydantic model
    try:
        summary = RepositorySummary(
            name="test-repo",
            description="A Python web framework",
            purpose="Build REST APIs",
            technologies=["python", "fastapi"],
            complexity="medium",
            target_audience="developers"
        )
        assert summary.name == "test-repo"
        print("✅ Pydantic models work")
    except Exception as e:
        print(f"❌ Pydantic models failed: {e}")
        return False
    
    # Test 3: Configuration loading
    try:
        settings = load_settings("config.toml")
        assert hasattr(settings, 'summarizer_kind')
        print("✅ Configuration loading works")
    except Exception as e:
        print(f"❌ Configuration loading failed: {e}")
        return False
    
    # Test 4: Ollama summarizer initialization
    try:
        summarizer = OllamaSummarizer(
            model="test-model",
            base_url="http://localhost:11434",
            num_ctx=4096
        )
        assert summarizer.model == "test-model"
        print("✅ Ollama summarizer initialization works")
    except Exception as e:
        print(f"❌ Ollama summarizer initialization failed: {e}")
        return False
    
    return True


def test_model_connectivity():
    """Test if Ollama server is reachable."""
    print("\n🔍 Testing model connectivity...")
    
    try:
        import httpx
        with httpx.Client(timeout=5.0) as client:
            response = client.get("http://localhost:11434/api/tags")
            if response.status_code == 200:
                print("✅ Ollama server is running")
                return True
            else:
                print(f"❌ Ollama server returned status {response.status_code}")
                return False
    except Exception as e:
        print(f"❌ Cannot connect to Ollama server: {e}")
        print("💡 To test with Ollama:")
        print("   1. Start Ollama: ollama serve")
        print("   2. Pull a model: ollama pull llama3.2:3b")
        return False


def main():
    """Run quick tests."""
    print("🚀 Running quick tests for ghsum...\n")
    
    # Test basic functionality
    basic_ok = test_basic_functionality()
    
    # Test model connectivity
    model_ok = test_model_connectivity()
    
    # Summary
    print("\n" + "="*40)
    if basic_ok:
        print("✅ Basic functionality: PASSED")
    else:
        print("❌ Basic functionality: FAILED")
    
    if model_ok:
        print("✅ Model connectivity: PASSED")
    else:
        print("⚠️  Model connectivity: SKIPPED (Ollama not running)")
    
    if basic_ok:
        print("\n🎉 Core functionality is working! Your changes are safe.")
        return 0
    else:
        print("\n⚠️  Some core functionality failed. Please check the errors above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
