"""
MediaGrab Backend – Configuration
Environment variables are prefixed with MEDIAGRAB_
Example: MEDIAGRAB_PORT=9000

Copy .env.example to .env and customize.
"""

from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    host: str = "0.0.0.0"
    port: int = 8000
    output_dir: str = "~/Downloads/MediaGrab"
    cors_origins: list[str] = ["http://localhost", "http://localhost:8081", "exp://"]
    max_concurrent_downloads: int = 3
    debug: bool = False
    log_level: str = "info"
    api_key: str = ""

    # Donation settings
    flw_secret_key: str = ""
    flw_public_key: str = ""
    flw_secret_hash: str = ""
    stripe_secret_key: str = ""
    paypal_client_id: str = ""
    paypal_client_secret: str = ""
    nowpayments_api_key: str = ""
    nowpayments_ipn_secret: str = ""
    coinbase_commerce_api_key: str = ""
    wallet_btc: str = ""
    wallet_eth: str = ""
    wallet_sol: str = ""
    wallet_usdc: str = ""
    wallet_usdt: str = ""
    donation_default_currency: str = "KES"
    donation_campaign_id: str = "mediagrab"
    donation_merchant_name: str = "MediaGrab"
    donation_redirect_success: str = ""
    donation_redirect_cancel: str = ""
    donation_crypto_enabled: bool = True
    donation_crypto_provider_priority: str = "nowpayments,direct"

    model_config = {"env_prefix": "MEDIAGRAB_", "env_file": ".env", "extra": "ignore"}


@lru_cache
def get_settings() -> Settings:
    return Settings()
