#!/usr/bin/env python3
"""Ultra-simple test to verify ghsum works."""

def test_imports():
    """Test that all imports work."""
    try:
        from ghsum.summarizer import basic_summary, OllamaSummarizer, RepositorySummary
        from ghsum.config import load_settings
        from ghsum.github import list_user_repos
        print("✅ All imports successful")
        return True
    except Exception as e:
        print(f"❌ Import failed: {e}")
        return False

def test_basic_summary():
    """Test basic summary function."""
    try:
        from ghsum.summarizer import basic_summary
        result = basic_summary("test-repo", "A Python web framework", "Web framework")
        assert isinstance(result, str)
        assert len(result) > 0
        print("✅ Basic summary works")
        return True
    except Exception as e:
        print(f"❌ Basic summary failed: {e}")
        return False

def test_pydantic_model():
    """Test Pydantic model creation."""
    try:
        from ghsum.summarizer import RepositorySummary
        summary = RepositorySummary(
            name="test-repo",
            description="A Python web framework",
            purpose="Build APIs",
            technologies=["python", "fastapi"],
            complexity="medium",
            target_audience="developers"
        )
        assert summary.name == "test-repo"
        print("✅ Pydantic model works")
        return True
    except Exception as e:
        print(f"❌ Pydantic model failed: {e}")
        return False

if __name__ == "__main__":
    print("🧪 Running simple tests...\n")
    
    tests = [
        test_imports,
        test_basic_summary,
        test_pydantic_model
    ]
    
    passed = 0
    for test in tests:
        if test():
            passed += 1
        print()
    
    print(f"Results: {passed}/{len(tests)} tests passed")
    
    if passed == len(tests):
        print("🎉 All tests passed! Your setup is working.")
    else:
        print("⚠️  Some tests failed. Check the errors above.")
