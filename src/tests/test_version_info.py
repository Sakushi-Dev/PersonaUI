"""
Tests for version info utility in helpers.py
"""
import pytest
import json
import os
from unittest.mock import patch, mock_open
import sys

# Import the function to test
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from utils import helpers


class TestVersionInfo:
    """Test cases for get_version_info function"""
    
    def setup_method(self):
        """Reset cache before each test"""
        helpers._version_cache = None
    
    def test_valid_version_json(self):
        """Test reading valid version.json file"""
        # Mock version.json content
        version_data = {"version": "1.2.3"}
        
        with patch("builtins.open", mock_open(read_data=json.dumps(version_data))):
            result = helpers.get_version_info()
        
        assert result["version"] == "1.2.3"
        assert result["major"] == 1
        assert result["minor"] == 2
        assert result["patch"] == "3"
    
    def test_missing_file(self):
        """Test behavior when version.json is missing"""
        with patch("builtins.open", side_effect=FileNotFoundError("File not found")):
            result = helpers.get_version_info()
        
        assert result["version"] == "unknown"
        assert result["major"] == 0
        assert result["minor"] == 0
        assert result["patch"] == "0"
    
    def test_invalid_json(self):
        """Test behavior with invalid JSON content"""
        with patch("builtins.open", mock_open(read_data="invalid json content")):
            result = helpers.get_version_info()
        
        assert result["version"] == "unknown"
        assert result["major"] == 0
        assert result["minor"] == 0
        assert result["patch"] == "0"
    
    def test_caching(self):
        """Test that result is cached (same object returned)"""
        version_data = {"version": "2.0.1"}
        
        with patch("builtins.open", mock_open(read_data=json.dumps(version_data))):
            result1 = helpers.get_version_info()
            result2 = helpers.get_version_info()
        
        # Same object (cached)
        assert result1 is result2
        assert result1["version"] == "2.0.1"
    
    def test_version_formats(self):
        """Test various version string formats"""
        test_cases = [
            # (input, expected_major, expected_minor, expected_patch)
            ("1.2.3", 1, 2, "3"),
            ("2.0.1-beta", 2, 0, "1"),
            ("10", 10, 0, "0"),
            ("1.5", 1, 5, "0"),
            ("0.3.2-alpha", 0, 3, "2")
        ]
        
        for version_str, exp_major, exp_minor, exp_patch in test_cases:
            helpers._version_cache = None  # Reset cache
            version_data = {"version": version_str}
            
            with patch("builtins.open", mock_open(read_data=json.dumps(version_data))):
                result = helpers.get_version_info()
            
            assert result["version"] == version_str, f"Failed for {version_str}"
            assert result["major"] == exp_major, f"Major failed for {version_str}"
            assert result["minor"] == exp_minor, f"Minor failed for {version_str}"
            assert result["patch"] == exp_patch, f"Patch failed for {version_str}"
    
    def test_missing_version_key(self):
        """Test behavior when version key is missing from JSON"""
        version_data = {"other_field": "value"}
        
        with patch("builtins.open", mock_open(read_data=json.dumps(version_data))):
            result = helpers.get_version_info()
        
        assert result["version"] == "unknown"
        assert result["major"] == 0
        assert result["minor"] == 0
        assert result["patch"] == "0"


if __name__ == "__main__":
    pytest.main([__file__])
