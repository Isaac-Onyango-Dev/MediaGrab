"""
MediaGrab Backend - Configuration Tests
Tests for configuration loading, validation, and environment variable handling
"""

import os
import pytest
from unittest.mock import patch, mock_open
from pathlib import Path

from config import Settings, get_settings


# Reset the cached settings before each test
@pytest.fixture(autouse=True)
def reset_settings_cache():
    """Reset the LRU cache for settings to ensure clean state"""
    get_settings.cache_clear()


# ------------------------------
# Basic Configuration Tests
# ------------------------------

def test_settings_loading():
    """Test configuration loading with default values"""
    settings = get_settings()
    
    assert settings.host == "0.0.0.0"
    assert settings.port == 8000
    assert settings.output_dir == "~/Downloads/MediaGrab"
    assert settings.max_concurrent_downloads == 3
    assert settings.debug is False
    assert settings.log_level == "info"
    assert settings.api_key == ""


def test_settings_from_environment_variables():
    """Test settings loading from environment variables"""
    env_vars = {
        "MEDIAGRAB_HOST": "127.0.0.1",
        "MEDIAGRAB_PORT": "9000",
        "MEDIAGRAB_OUTPUT_DIR": "/custom/downloads",
        "MEDIAGRAB_MAX_CONCURRENT_DOWNLOADS": "5",
        "MEDIAGRAB_DEBUG": "true",
        "MEDIAGRAB_LOG_LEVEL": "debug",
        "MEDIAGRAB_API_KEY": "test-api-key-123"
    }
    
    with patch.dict(os.environ, env_vars):
        settings = get_settings()
        
        assert settings.host == "127.0.0.1"
        assert settings.port == 9000
        assert settings.output_dir == "/custom/downloads"
        assert settings.max_concurrent_downloads == 5
        assert settings.debug is True
        assert settings.log_level == "debug"
        assert settings.api_key == "test-api-key-123"


def test_settings_type_validation():
    """Test settings type validation and conversion"""
    env_vars = {
        "MEDIAGRAB_PORT": "invalid_port",  # Should remain default
        "MEDIAGRAB_MAX_CONCURRENT_DOWNLOADS": "not_a_number",  # Should remain default
        "MEDIAGRAB_DEBUG": "1",  # Should convert to True
        "MEDIAGRAB_CORS_ORIGINS": '["http://example.com", "https://app.test"]'  # Should parse as list
    }
    
    with patch.dict(os.environ, env_vars):
        settings = get_settings()
        
        # Invalid values should fall back to defaults
        assert settings.port == 8000
        assert settings.max_concurrent_downloads == 3
        
        # Valid conversions should work
        assert settings.debug is True


def test_settings_cors_origins_parsing():
    """Test CORS origins list parsing"""
    env_vars = {
        "MEDIAGRAB_CORS_ORIGINS": '["http://localhost:3000", "https://app.example.com", "exp://127.0.0.1:19000"]'
    }
    
    with patch.dict(os.environ, env_vars):
        settings = get_settings()
        
        assert len(settings.cors_origins) == 3
        assert "http://localhost:3000" in settings.cors_origins
        assert "https://app.example.com" in settings.cors_origins
        assert "exp://127.0.0.1:19000" in settings.cors_origins


def test_settings_caching():
    """Test that settings are cached properly"""
    # First call
    settings1 = get_settings()
    
    # Second call should return cached instance
    settings2 = get_settings()
    
    assert settings1 is settings2
    assert id(settings1) == id(settings2)


def test_settings_cache_invalidation():
    """Test cache invalidation when environment changes"""
    # First call with default environment
    settings1 = get_settings()
    assert settings1.port == 8000
    
    # Change environment
    with patch.dict(os.environ, {"MEDIAGRAB_PORT": "9000"}):
        # Cache should be cleared by fixture, so new settings are loaded
        settings2 = get_settings()
        assert settings2.port == 9000
    
    # Back to default after environment context
    settings3 = get_settings()
    assert settings3.port == 8000


# ------------------------------
# Environment File Tests
# ------------------------------

def test_env_file_loading():
    """Test loading configuration from .env file"""
    env_content = """
# MediaGrab Configuration
MEDIAGRAB_HOST=127.0.0.1
MEDIAGRAB_PORT=9000
MEDIAGRAB_DEBUG=true
MEDIAGRAB_API_KEY=env-file-key
# Comment line should be ignored
MEDIAGRAB_OUTPUT_DIR=/env/downloads
"""
    
    with patch("builtins.open", mock_open(read_data=env_content)):
        with patch("pathlib.Path.exists", return_value=True):
            settings = get_settings()
            
            assert settings.host == "127.0.0.1"
            assert settings.port == 9000
            assert settings.debug is True
            assert settings.api_key == "env-file-key"
            assert settings.output_dir == "/env/downloads"


def test_env_file_missing():
    """Test behavior when .env file doesn't exist"""
    with patch("pathlib.Path.exists", return_value=False):
        settings = get_settings()
        
        # Should use defaults when .env file is missing
        assert settings.host == "0.0.0.0"
        assert settings.port == 8000
        assert settings.debug is False


def test_env_file_corrupted():
    """Test handling of corrupted .env file"""
    env_content = """
MEDIAGRAB_HOST=127.0.0.1
INVALID_SYNTAX_LINE
MEDIAGRAB_PORT=9000
"""
    
    with patch("builtins.open", mock_open(read_data=env_content)):
        with patch("pathlib.Path.exists", return_value=True):
            # Should handle corrupted file gracefully
            settings = get_settings()
            
            # Valid lines should still be processed
            assert settings.host == "127.0.0.1"
            assert settings.port == 9000


def test_env_file_precedence():
    """Test that environment variables override .env file"""
    env_content = """
MEDIAGRAB_HOST=127.0.0.1
MEDIAGRAB_PORT=9000
MEDIAGRAB_DEBUG=false
"""
    
    with patch("builtins.open", mock_open(read_data=env_content)):
        with patch("pathlib.Path.exists", return_value=True):
            with patch.dict(os.environ, {
                "MEDIAGRAB_HOST": "192.168.1.100",  # Override .env
                "MEDIAGRAB_DEBUG": "true"  # Override .env
            }):
                settings = get_settings()
                
                # Environment variables should take precedence
                assert settings.host == "192.168.1.100"
                assert settings.port == 9000  # From .env
                assert settings.debug is True  # From environment


# ------------------------------
# Donation Configuration Tests
# ------------------------------

def test_donation_settings_defaults():
    """Test donation settings default values"""
    settings = get_settings()
    
    assert settings.flw_secret_key == ""
    assert settings.stripe_secret_key == ""
    assert settings.paypal_client_id == ""
    assert settings.nowpayments_api_key == ""
    assert settings.coinbase_commerce_api_key == ""
    assert settings.donation_default_currency == "KES"
    assert settings.donation_campaign_id == "mediagrab"
    assert settings.donation_merchant_name == "MediaGrab"
    assert settings.donation_crypto_enabled is True
    assert settings.donation_crypto_provider_priority == "nowpayments,direct"


def test_donation_settings_from_env():
    """Test donation settings from environment variables"""
    env_vars = {
        "MEDIAGRAB_FLW_SECRET_KEY": "flutterwave-secret",
        "MEDIAGRAB_STRIPE_SECRET_KEY": "stripe-secret",
        "MEDIAGRAB_PAYPAL_CLIENT_ID": "paypal-client",
        "MEDIAGRAB_DONATION_DEFAULT_CURRENCY": "USD",
        "MEDIAGRAB_DONATION_CRYPTO_ENABLED": "false"
    }
    
    with patch.dict(os.environ, env_vars):
        settings = get_settings()
        
        assert settings.flw_secret_key == "flutterwave-secret"
        assert settings.stripe_secret_key == "stripe-secret"
        assert settings.paypal_client_id == "paypal-client"
        assert settings.donation_default_currency == "USD"
        assert settings.donation_crypto_enabled is False


def test_crypto_wallet_settings():
    """Test cryptocurrency wallet configuration"""
    env_vars = {
        "MEDIAGRAB_WALLET_BTC": "bc1qexample",
        "MEDIAGRAB_WALLET_ETH": "0xexample",
        "MEDIAGRAB_WALLET_SOL": "exampleSolana",
        "MEDIAGRAB_WALLET_USDC": "0xusdc",
        "MEDIAGRAB_WALLET_USDT": "0xusdt"
    }
    
    with patch.dict(os.environ, env_vars):
        settings = get_settings()
        
        assert settings.wallet_btc == "bc1qexample"
        assert settings.wallet_eth == "0xexample"
        assert settings.wallet_sol == "exampleSolana"
        assert settings.wallet_usdc == "0xusdc"
        assert settings.wallet_usdt == "0xusdt"


# ------------------------------
# Validation Tests
# ------------------------------

def test_port_range_validation():
    """Test port number validation"""
    # Valid ports
    valid_ports = ["80", "443", "8000", "8080", "9000"]
    
    for port in valid_ports:
        with patch.dict(os.environ, {"MEDIAGRAB_PORT": port}):
            settings = get_settings()
            assert settings.port == int(port)


def test_concurrent_downloads_validation():
    """Test concurrent downloads validation"""
    # Valid values
    valid_values = ["1", "2", "3", "5", "10"]
    
    for value in valid_values:
        with patch.dict(os.environ, {"MEDIAGRAB_MAX_CONCURRENT_DOWNLOADS": value}):
            settings = get_settings()
            assert settings.max_concurrent_downloads == int(value)


def test_log_level_validation():
    """Test log level validation"""
    valid_levels = ["debug", "info", "warning", "error", "critical"]
    
    for level in valid_levels:
        with patch.dict(os.environ, {"MEDIAGRAB_LOG_LEVEL": level}):
            settings = get_settings()
            assert settings.log_level.lower() == level


def test_boolean_validation():
    """Test boolean field validation"""
    boolean_tests = [
        ("true", True),
        ("True", True),
        ("TRUE", True),
        ("1", True),
        ("false", False),
        ("False", False),
        ("FALSE", False),
        ("0", False),
        ("", False)  # Empty string should be False
    ]
    
    for env_value, expected in boolean_tests:
        with patch.dict(os.environ, {"MEDIAGRAB_DEBUG": env_value}):
            settings = get_settings()
            assert settings.debug is expected


# ------------------------------
# Security Tests
# ------------------------------

def test_sensitive_data_handling():
    """Test that sensitive data is handled properly"""
    env_vars = {
        "MEDIAGRAB_API_KEY": "super-secret-api-key",
        "MEDIAGRAB_FLW_SECRET_KEY": "flutterwave-secret",
        "MEDIAGRAB_STRIPE_SECRET_KEY": "stripe-secret",
        "MEDIAGRAB_PAYPAL_CLIENT_SECRET": "paypal-secret"
    }
    
    with patch.dict(os.environ, env_vars):
        settings = get_settings()
        
        # Sensitive data should be accessible but not logged
        assert settings.api_key == "super-secret-api-key"
        assert settings.flw_secret_key == "flutterwave-secret"
        assert settings.stripe_secret_key == "stripe-secret"
        assert settings.paypal_client_secret == "paypal-secret"


def test_api_key_required_in_production():
    """Test API key requirement in production environment"""
    env_vars = {
        "MEDIAGRAB_DEBUG": "false",  # Production mode
        # MEDIAGRAB_API_KEY not set
    }
    
    with patch.dict(os.environ, env_vars):
        settings = get_settings()
        
        # In production, API key should be required
        # This test verifies the configuration loads, but application logic
        # should enforce API key requirement
        assert settings.api_key == ""
        assert settings.debug is False


# ------------------------------
# Configuration Edge Cases
# ------------------------------

def test_empty_environment_variables():
    """Test handling of empty environment variables"""
    env_vars = {
        "MEDIAGRAB_HOST": "",
        "MEDIAGRAB_API_KEY": "",
        "MEDIAGRAB_OUTPUT_DIR": ""
    }
    
    with patch.dict(os.environ, env_vars):
        settings = get_settings()
        
        # Empty strings should be handled appropriately
        assert settings.host == ""
        assert settings.api_key == ""
        assert settings.output_dir == ""


def test_whitespace_in_environment_variables():
    """Test handling of whitespace in environment variables"""
    env_vars = {
        "MEDIAGRAB_HOST": "  127.0.0.1  ",
        "MEDIAGRAB_API_KEY": "  test-key  ",
        "MEDIAGRAB_DEBUG": "  true  "
    }
    
    with patch.dict(os.environ, env_vars):
        settings = get_settings()
        
        # Whitespace handling depends on pydantic configuration
        # This test documents current behavior
        assert "127.0.0.1" in settings.host
        assert "test-key" in settings.api_key
        assert settings.debug is True


def test_unicode_in_environment_variables():
    """Test handling of unicode characters in environment variables"""
    env_vars = {
        "MEDIAGRAB_HOST": "localhost",
        "MEDIAGRAB_OUTPUT_DIR": "/downloads/ MédiaGrab",
        "MEDIAGRAB_DONATION_MERCHANT_NAME": "MediaGrab Café"
    }
    
    with patch.dict(os.environ, env_vars):
        settings = get_settings()
        
        assert settings.host == "localhost"
        assert "MédiaGrab" in settings.output_dir
        assert "Café" in settings.donation_merchant_name


# ------------------------------
# Configuration Integration Tests
# ------------------------------

def test_full_configuration_integration():
    """Test complete configuration integration"""
    env_content = """
# Basic settings
MEDIAGRAB_HOST=127.0.0.1
MEDIAGRAB_PORT=8080
MEDIAGRAB_DEBUG=true
MEDIAGRAB_LOG_LEVEL=debug

# Security
MEDIAGRAB_API_KEY=integration-test-key

# Download settings
MEDIAGRAB_OUTPUT_DIR=/test/downloads
MEDIAGRAB_MAX_CONCURRENT_DOWNLOADS=5

# CORS
MEDIAGRAB_CORS_ORIGINS=["http://localhost:3000", "https://app.test"]

# Donation settings
MEDIAGRAB_DONATION_DEFAULT_CURRENCY=USD
MEDIAGRAB_DONATION_CRYPTO_ENABLED=true
MEDIAGRAB_WALLET_BTC=btc-test-address
"""
    
    # Override some values with environment variables
    env_overrides = {
        "MEDIAGRAB_PORT": "9000",  # Override .env file
        "MEDIAGRAB_API_KEY": "env-override-key"
    }
    
    with patch("builtins.open", mock_open(read_data=env_content)):
        with patch("pathlib.Path.exists", return_value=True):
            with patch.dict(os.environ, env_overrides):
                settings = get_settings()
                
                # Verify integration
                assert settings.host == "127.0.0.1"  # From .env
                assert settings.port == 9000  # From environment override
                assert settings.debug is True  # From .env
                assert settings.log_level == "debug"  # From .env
                assert settings.api_key == "env-override-key"  # From environment
                assert settings.output_dir == "/test/downloads"  # From .env
                assert settings.max_concurrent_downloads == 5  # From .env
                assert len(settings.cors_origins) == 2  # From .env
                assert settings.donation_default_currency == "USD"  # From .env
                assert settings.donation_crypto_enabled is True  # From .env
                assert settings.wallet_btc == "btc-test-address"  # From .env


def test_configuration_model_extra_ignore():
    """Test that extra fields are ignored as per model configuration"""
    env_vars = {
        "MEDIAGRAB_HOST": "127.0.0.1",
        "MEDIAGRAB_UNKNOWN_FIELD": "should_be_ignored",
        "MEDIAGRAB_ANOTHER_UNKNOWN": "also_ignored"
    }
    
    with patch.dict(os.environ, env_vars):
        settings = get_settings()
        
        # Should load known fields successfully
        assert settings.host == "127.0.0.1"
        
        # Unknown fields should be ignored (not raise errors)
        # This is the behavior specified by extra="ignore"
        assert not hasattr(settings, "unknown_field")
        assert not hasattr(settings, "another_unknown")


# ------------------------------
# Performance Tests
# ------------------------------

def test_settings_loading_performance():
    """Test that settings loading is performant"""
    import time
    
    # Test multiple calls to ensure caching works
    start_time = time.time()
    
    for _ in range(100):
        get_settings.cache_clear()
        get_settings()
    
    end_time = time.time()
    
    # Should complete quickly (less than 1 second for 100 calls)
    assert end_time - start_time < 1.0


def test_cached_settings_performance():
    """Test that cached settings access is fast"""
    import time
    
    # First call to populate cache
    get_settings()
    
    start_time = time.time()
    
    # Multiple cached calls should be very fast
    for _ in range(1000):
        get_settings()
    
    end_time = time.time()
    
    # Cached calls should be extremely fast
    assert end_time - start_time < 0.1
