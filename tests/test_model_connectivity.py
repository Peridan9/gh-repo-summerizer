"""Test model connectivity and basic functionality."""

import pytest
import os
from unittest.mock import patch, MagicMock
from ghsum.summarizer import OllamaSummarizer


class TestModelConnectivity:
    """Test that the model can receive requests and provide responses."""
    
    def test_ollama_server_connection(self):
        """Test if Ollama server is reachable."""
        try:
            import httpx
            with httpx.Client(timeout=5.0) as client:
                response = client.get("http://localhost:11434/api/tags")
                if response.status_code == 200:
                    print("✅ Ollama server is running")
                    return True
                else:
                    print("❌ Ollama server returned non-200 status")
                    return False
        except Exception as e:
            print(f"❌ Cannot connect to Ollama server: {e}")
            return False
    
    @pytest.mark.skipif(not os.getenv("TEST_WITH_OLLAMA"), reason="Ollama server not available")
    def test_actual_ollama_request(self):
        """Test actual request to Ollama server (only if TEST_WITH_OLLAMA env var is set)."""
        summarizer = OllamaSummarizer(
            model="llama3.2:3b",  # or whatever model you have
            base_url="http://localhost:11434",
            num_ctx=2048  # Smaller context for faster testing
        )
        
        try:
            result = summarizer.summarize(
                "test-repo",
                "A simple Python web framework for building REST APIs",
                "Web framework"
            )
            assert isinstance(result, str)
            assert len(result) > 0
            print(f"✅ Model response: {result[:100]}...")
            return True
        except Exception as e:
            print(f"❌ Model request failed: {e}")
            return False
    
    @pytest.mark.skipif(not os.getenv("TEST_WITH_OLLAMA"), reason="Ollama server not available")
    def test_structured_ollama_request(self):
        """Test structured request to Ollama server."""
        summarizer = OllamaSummarizer(
            model="llama3.2:3b",
            base_url="http://localhost:11434",
            num_ctx=2048
        )
        
        try:
            result = summarizer.summarize_structured(
                "test-repo",
                "A simple Python web framework for building REST APIs",
                "Web framework",
                "python, fastapi"
            )
            assert isinstance(result, RepositorySummary)
            assert result.name == "test-repo"
            assert len(result.description) > 0
            print(f"✅ Structured response: {result.description}")
            return True
        except Exception as e:
            print(f"❌ Structured model request failed: {e}")
            return False


def run_connectivity_tests():
    """Run connectivity tests and print results."""
    print("🔍 Testing model connectivity...")
    
    # Test 1: Basic server connection
    connectivity_test = TestModelConnectivity()
    server_ok = connectivity_test.test_ollama_server_connection()
    
    if not server_ok:
        print("\n💡 To test with actual Ollama server:")
        print("   1. Start Ollama: ollama serve")
        print("   2. Pull a model: ollama pull llama3.2:3b")
        print("   3. Set env var: export TEST_WITH_OLLAMA=1")
        print("   4. Run: python -m pytest tests/test_model_connectivity.py -v")
        return False
    
    # Test 2: Actual model request (if available)
    if os.getenv("TEST_WITH_OLLAMA"):
        print("\n🤖 Testing actual model requests...")
        connectivity_test.test_actual_ollama_request()
        connectivity_test.test_structured_ollama_request()
    
    return True


if __name__ == "__main__":
    run_connectivity_tests()
