"""Basic functionality tests for ghsum package."""

import pytest
import json
from unittest.mock import patch, MagicMock
from ghsum.summarizer import basic_summary, OllamaSummarizer, RepositorySummary
from ghsum.github import list_user_repos, get_languages, get_readme
from ghsum.config import load_settings


class TestBasicSummarizer:
    """Test the basic (no-LLM) summarizer."""
    
    def test_basic_summary_with_description(self):
        """Test basic summary with a description."""
        result = basic_summary("test-repo", "A simple Python web framework", "Web framework")
        assert isinstance(result, str)
        assert len(result) > 0
        assert len(result.split()) <= 90  # Should be capped at ~90 words
    
    def test_basic_summary_with_readme(self):
        """Test basic summary with README content."""
        readme_content = """
        # My Project
        
        This is a Python web framework built with FastAPI.
        It provides REST API endpoints for user management.
        """
        result = basic_summary("my-project", readme_content, "")
        assert isinstance(result, str)
        assert "Python" in result or "web" in result or "framework" in result
    
    def test_basic_summary_fallback(self):
        """Test basic summary fallback when no content."""
        result = basic_summary("empty-repo", "", "")
        assert isinstance(result, str)
        assert result == "empty-repo"  # Should fallback to repo name


class TestOllamaSummarizer:
    """Test Ollama summarizer (with mocking)."""
    
    def test_ollama_initialization(self):
        """Test Ollama summarizer initialization."""
        summarizer = OllamaSummarizer(
            model="test-model",
            base_url="http://localhost:11434",
            num_ctx=4096
        )
        assert summarizer.model == "test-model"
        assert summarizer.base_url == "http://localhost:11434"
        assert summarizer.num_ctx == 4096
    
    @patch('httpx.Client')
    def test_ollama_summarize_success(self, mock_client):
        """Test successful Ollama summarization."""
        # Mock successful response
        mock_response = MagicMock()
        mock_response.json.return_value = {"response": "This is a Python web framework for building APIs."}
        mock_response.raise_for_status.return_value = None
        
        mock_client.return_value.__enter__.return_value.post.return_value = mock_response
        
        summarizer = OllamaSummarizer(model="test-model")
        result = summarizer.summarize("test-repo", "A Python web framework", "Web framework")
        
        assert isinstance(result, str)
        assert "Python" in result or "web" in result or "framework" in result
    
    @patch('httpx.Client')
    def test_ollama_structured_success(self, mock_client):
        """Test successful structured Ollama summarization."""
        # Mock successful JSON response
        mock_json_response = {
            "name": "test-repo",
            "description": "A Python web framework",
            "purpose": "Build REST APIs",
            "technologies": ["python", "fastapi"],
            "complexity": "medium",
            "target_audience": "developers"
        }
        
        mock_response = MagicMock()
        mock_response.json.return_value = {"response": json.dumps(mock_json_response)}
        mock_response.raise_for_status.return_value = None
        
        mock_client.return_value.__enter__.return_value.post.return_value = mock_response
        
        summarizer = OllamaSummarizer(model="test-model")
        result = summarizer.summarize_structured("test-repo", "A Python web framework", "Web framework")
        
        assert isinstance(result, RepositorySummary)
        assert result.name == "test-repo"
        assert "Python" in result.description
        assert "python" in result.technologies
    
    @patch('httpx.Client')
    def test_ollama_structured_fallback(self, mock_client):
        """Test structured summarization fallback on invalid JSON."""
        # Mock response with invalid JSON
        mock_response = MagicMock()
        mock_response.json.return_value = {"response": "This is not valid JSON"}
        mock_response.raise_for_status.return_value = None
        
        mock_client.return_value.__enter__.return_value.post.return_value = mock_response
        
        summarizer = OllamaSummarizer(model="test-model")
        result = summarizer.summarize_structured("test-repo", "A Python web framework", "Web framework")
        
        # Should fallback to default values
        assert isinstance(result, RepositorySummary)
        assert result.name == "test-repo"
        assert result.description == "Web framework" or result.description == "Repository summary"


class TestPydanticModels:
    """Test Pydantic model validation."""
    
    def test_repository_summary_valid(self):
        """Test valid RepositorySummary creation."""
        summary = RepositorySummary(
            name="test-repo",
            description="A Python web framework",
            purpose="Build REST APIs",
            technologies=["python", "fastapi"],
            complexity="medium",
            target_audience="developers"
        )
        assert summary.name == "test-repo"
        assert summary.complexity == "medium"
        assert "python" in summary.technologies
    
    def test_repository_summary_validation(self):
        """Test RepositorySummary validation."""
        # Test technology list validation
        with pytest.raises(ValueError, match="Too many technologies"):
            RepositorySummary(
                name="test",
                description="test",
                purpose="test",
                technologies=["python", "fastapi", "pydantic", "httpx", "uvicorn", "gunicorn"]  # 6 items > 5
            )
        
        # Test complexity validation
        with pytest.raises(ValueError, match="Complexity must be one of"):
            RepositorySummary(
                name="test",
                description="test", 
                purpose="test",
                technologies=["python"],
                complexity="invalid"
            )


class TestConfiguration:
    """Test configuration loading."""
    
    def test_load_settings_default(self):
        """Test loading settings with defaults."""
        settings = load_settings("nonexistent_config.toml")
        assert settings.summarizer_kind == "basic"
        assert settings.model == "llama3.2:3b"
        assert settings.num_ctx == 8192
    
    def test_load_settings_with_config(self):
        """Test loading settings with actual config file."""
        # This will use your existing config.toml
        settings = load_settings("config.toml")
        assert hasattr(settings, 'summarizer_kind')
        assert hasattr(settings, 'model')
        assert hasattr(settings, 'num_ctx')


class TestGitHubAPI:
    """Test GitHub API functions (with mocking)."""
    
    @patch('httpx.Client')
    def test_list_user_repos_success(self, mock_client):
        """Test successful repository listing."""
        # Mock successful response
        mock_response = MagicMock()
        mock_response.json.return_value = [
            {
                "name": "test-repo",
                "html_url": "https://github.com/user/test-repo",
                "description": "A test repository",
                "fork": False,
                "archived": False
            }
        ]
        mock_response.raise_for_status.return_value = None
        
        mock_client.return_value.__enter__.return_value.get.return_value = mock_response
        
        repos = list_user_repos("testuser")
        assert len(repos) == 1
        assert repos[0]["name"] == "test-repo"
    
    @patch('httpx.Client')
    def test_get_languages_success(self, mock_client):
        """Test successful language retrieval."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"Python": 1000, "JavaScript": 500}
        mock_response.raise_for_status.return_value = None
        
        mock_client.return_value.__enter__.return_value.get.return_value = mock_response
        
        langs = get_languages("user", "repo")
        assert langs["Python"] == 1000
        assert langs["JavaScript"] == 500
    
    @patch('httpx.Client')
    def test_get_readme_success(self, mock_client):
        """Test successful README retrieval."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "encoding": "base64",
            "content": "IyBUZXN0IFJlYWRNRQ=="  # "# Test README" in base64
        }
        mock_response.raise_for_status.return_value = None
        
        mock_client.return_value.__enter__.return_value.get.return_value = mock_response
        
        readme = get_readme("user", "repo")
        assert readme == "# Test README"
    
    @patch('httpx.Client')
    def test_get_readme_not_found(self, mock_client):
        """Test README not found (404)."""
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.raise_for_status.side_effect = Exception("404")
        
        mock_client.return_value.__enter__.return_value.get.return_value = mock_response
        
        readme = get_readme("user", "repo")
        assert readme is None


class TestIntegration:
    """Integration tests that test multiple components together."""
    
    def test_basic_workflow(self):
        """Test the basic workflow without external dependencies."""
        # Test that basic summary works
        result = basic_summary("test-repo", "A Python web framework", "Web framework")
        assert isinstance(result, str)
        assert len(result) > 0
    
    def test_ollama_initialization_with_config(self):
        """Test Ollama summarizer with configuration."""
        summarizer = OllamaSummarizer(
            model="llama3.2:3b",
            base_url="http://localhost:11434",
            num_ctx=8192
        )
        assert summarizer.model == "llama3.2:3b"
        assert summarizer.base_url == "http://localhost:11434"
        assert summarizer.num_ctx == 8192


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
