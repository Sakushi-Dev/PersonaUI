"""
Tests for version info utility in helpers.py
"""
import pytest
import os
from unittest.mock import patch, MagicMock
import sys
import configparser

# Import the function to test
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from utils import helpers


class TestVersionInfo:
    """Test cases for get_version_info function"""
    
    def setup_method(self):
        """Reset cache before each test"""
        helpers._version_cache = None
    
    def test_valid_version_ini(self):
        """Test reading valid version.ini file"""
        cp = configparser.ConfigParser()
        cp.read_string("[version]\nversion = 1.2.3\n")
        cp.read = MagicMock()
        
        with patch.object(helpers.configparser, 'ConfigParser', return_value=cp):
            result = helpers.get_version_info()
        
        assert result["version"] == "1.2.3"
        assert result["major"] == 1
        assert result["minor"] == 2
        assert result["patch"] == "3"
    
    def test_missing_file(self):
        """Test behavior when version.ini is missing/empty"""
        cp = configparser.ConfigParser()
        cp.read = MagicMock()
        
        with patch.object(helpers.configparser, 'ConfigParser', return_value=cp):
            result = helpers.get_version_info()
        
        assert result["version"] == "unknown"
        assert result["major"] == 0
        assert result["minor"] == 0
        assert result["patch"] == "0"
    
    def test_caching(self):
        """Test that result is cached (same object returned)"""
        cp = configparser.ConfigParser()
        cp.read_string("[version]\nversion = 2.0.1\n")
        cp.read = MagicMock()
        
        with patch.object(helpers.configparser, 'ConfigParser', return_value=cp):
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
            
            cp = configparser.ConfigParser()
            cp.read_string(f"[version]\nversion = {version_str}\n")
            cp.read = MagicMock()
            
            with patch.object(helpers.configparser, 'ConfigParser', return_value=cp):
                result = helpers.get_version_info()
            
            assert result["version"] == version_str, f"Failed for {version_str}"
            assert result["major"] == exp_major, f"Major failed for {version_str}"
            assert result["minor"] == exp_minor, f"Minor failed for {version_str}"
            assert result["patch"] == exp_patch, f"Patch failed for {version_str}"
    
    def test_missing_version_key(self):
        """Test behavior when version key is missing from ini"""
        cp = configparser.ConfigParser()
        cp.read_string("[other]\nfield = value\n")
        cp.read = MagicMock()
        
        with patch.object(helpers.configparser, 'ConfigParser', return_value=cp):
            result = helpers.get_version_info()
        
        assert result["version"] == "unknown"
        assert result["major"] == 0
        assert result["minor"] == 0
        assert result["patch"] == "0"


if __name__ == "__main__":
    pytest.main([__file__])
