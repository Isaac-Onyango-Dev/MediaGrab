"""
Donation Payment Handler for MediaGrab
=======================================
Supports:
  - Fiat: Flutterwave (Africa), Stripe (Global), PayPal (Fallback)
  - Crypto: NOWPayments (150+ coins), Coinbase Commerce, Direct Wallet
Features:
  - Geo-aware currency & payment method routing
  - Cryptocurrency payments (BTC, ETH, SOL, USDT, USDC, DAI, etc.)
  - Stablecoin auto-conversion for price stability
  - UUID-based idempotent transaction references
"""

import os
import re
import uuid
import time
import logging
import hashlib
import base64
from decimal import Decimal, InvalidOperation
from datetime import datetime, timezone
from typing import Any

import requests


logger = logging.getLogger("donation_payment")
_handler = logging.StreamHandler()
_handler.setFormatter(
    logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s | tx_ref=%(tx_ref)s | %(message)s",
        defaults={"tx_ref": "-"},
    )
)
logger.addHandler(_handler)
logger.setLevel(os.getenv("DONATION_LOG_LEVEL", "INFO"))


CURRENCY_REGISTRY = {
    "KES": {"symbol": "KSh", "decimals": 2, "region": "KE", "primary_provider": "flutterwave"},
    "NGN": {"symbol": "₦", "decimals": 2, "region": "NG", "primary_provider": "flutterwave"},
    "GHS": {"symbol": "GH₵", "decimals": 2, "region": "GH", "primary_provider": "flutterwave"},
    "ZAR": {"symbol": "R", "decimals": 2, "region": "ZA", "primary_provider": "flutterwave"},
    "UGX": {"symbol": "USh", "decimals": 0, "region": "UG", "primary_provider": "flutterwave"},
    "USD": {"symbol": "$", "decimals": 2, "region": "US", "primary_provider": "stripe"},
    "EUR": {"symbol": "€", "decimals": 2, "region": "EU", "primary_provider": "stripe"},
    "GBP": {"symbol": "£", "decimals": 2, "region": "GB", "primary_provider": "stripe"},
    "CAD": {"symbol": "CA$", "decimals": 2, "region": "CA", "primary_provider": "stripe"},
    "AUD": {"symbol": "A$", "decimals": 2, "region": "AU", "primary_provider": "stripe"},
    "INR": {"symbol": "₹", "decimals": 2, "region": "IN", "primary_provider": "stripe"},
}

COUNTRY_TO_CURRENCY = {
    "KE": "KES", "NG": "NGN", "GH": "GHS", "ZA": "ZAR", "UG": "UGX",
    "US": "USD", "GB": "GBP", "CA": "CAD", "AU": "AUD", "IN": "INR",
    "EU": "EUR", "DE": "EUR", "FR": "EUR", "ES": "EUR", "IT": "EUR",
}

CRYPTO_REGISTRY = {
    "BTC": {"name": "Bitcoin", "network": "bitcoin", "decimals": 8, "type": "native", "symbol": "₿"},
    "ETH": {"name": "Ethereum", "network": "ethereum", "decimals": 18, "type": "native", "symbol": "Ξ"},
    "SOL": {"name": "Solana", "network": "solana", "decimals": 9, "type": "native", "symbol": "◎"},
    "USDT": {"name": "Tether USD", "networks": ["ethereum", "tron", "bsc", "solana"], "decimals": 6, "type": "stablecoin", "symbol": "₮", "recommended_network": "solana"},
    "USDC": {"name": "USD Coin", "networks": ["ethereum", "solana", "polygon", "base"], "decimals": 6, "type": "stablecoin", "symbol": "USDC", "recommended_network": "solana"},
    "DAI": {"name": "Dai", "networks": ["ethereum", "polygon"], "decimals": 18, "type": "stablecoin", "symbol": "◈", "recommended_network": "polygon"},
    "LTC": {"name": "Litecoin", "network": "litecoin", "decimals": 8, "type": "native", "symbol": "Ł"},
}


class Config:
    FLW_SECRET_KEY = os.getenv("FLW_SECRET_KEY", "")
    FLW_PUBLIC_KEY = os.getenv("FLW_PUBLIC_KEY", "")
    FLW_SECRET_HASH = os.getenv("FLW_SECRET_HASH", "")
    STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY", "")
    PAYPAL_CLIENT_ID = os.getenv("PAYPAL_CLIENT_ID", "")
    PAYPAL_CLIENT_SECRET = os.getenv("PAYPAL_CLIENT_SECRET", "")
    NOWPAYMENTS_API_KEY = os.getenv("NOWPAYMENTS_API_KEY", "")
    NOWPAYMENTS_IPN_SECRET = os.getenv("NOWPAYMENTS_IPN_SECRET", "")
    COINBASE_COMMERCE_API_KEY = os.getenv("COINBASE_COMMERCE_API_KEY", "")
    WALLET_ADDRESSES = {
        coin.upper(): addr
        for coin, addr in {
            "BTC": os.getenv("WALLET_BTC", ""),
            "ETH": os.getenv("WALLET_ETH", ""),
            "SOL": os.getenv("WALLET_SOL", ""),
            "USDC": os.getenv("WALLET_USDC", ""),
            "USDT": os.getenv("WALLET_USDT", ""),
        }.items()
        if addr
    }
    DEFAULT_CURRENCY = os.getenv("DONATION_DEFAULT_CURRENCY", "KES")
    CAMPAIGN_ID = os.getenv("DONATION_CAMPAIGN_ID", "mediagrab")
    MERCHANT_NAME = os.getenv("DONATION_MERCHANT_NAME", "MediaGrab")
    CRYPTO_ENABLED = os.getenv("DONATION_CRYPTO_ENABLED", "true").lower() == "true"
    CRYPTO_PROVIDER_PRIORITY = os.getenv("DONATION_CRYPTO_PROVIDER_PRIORITY", "nowpayments,coinbase,direct").split(",")

    @classmethod
    def validate(cls):
        missing = []
        if not cls.FLW_SECRET_KEY:
            missing.append("FLW_SECRET_KEY")
        return missing

    @classmethod
    def get_wallet_address(cls, crypto):
        return cls.WALLET_ADDRESSES.get(crypto.upper())


class ValidationError(Exception):
    pass


class PaymentError(Exception):
    def __init__(self, message, provider="unknown"):
        super().__init__(message)
        self.provider = provider
        self.message = message


def validate_email(email):
    pattern = r"^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$"
    if not email or not re.match(pattern, email.strip()):
        raise ValidationError(f"Invalid email address: {email}")
    return email.strip().lower()


def validate_name(name):
    if not name or len(name.strip()) < 2:
        raise ValidationError("Donor name must be at least 2 characters")
    cleaned = re.sub(r"[^a-zA-Z0-9\s\-'.]", "", name.strip())
    if not cleaned:
        raise ValidationError("Donor name contains invalid characters")
    return cleaned


def validate_amount(amount, currency):
    try:
        amt = Decimal(str(amount))
    except (InvalidOperation, ValueError):
        raise ValidationError(f"Invalid amount: {amount}")
    if amt <= 0:
        raise ValidationError("Amount must be greater than 0")
    if currency.upper() in CRYPTO_REGISTRY and amt < Decimal("0.00000001"):
        raise ValidationError(f"Amount too small for {currency}")
    return amt


def resolve_currency(country_code, requested_currency):
    if requested_currency and requested_currency.upper() in CRYPTO_REGISTRY:
        return requested_currency.upper(), "crypto"
    if requested_currency and requested_currency.upper() in CURRENCY_REGISTRY:
        currency = requested_currency.upper()
        return currency, CURRENCY_REGISTRY[currency]["primary_provider"]
    if country_code and country_code.upper() in COUNTRY_TO_CURRENCY:
        currency = COUNTRY_TO_CURRENCY[country_code.upper()]
        return currency, CURRENCY_REGISTRY[currency]["primary_provider"]
    currency = Config.DEFAULT_CURRENCY
    return currency, CURRENCY_REGISTRY.get(currency, {}).get("primary_provider", "flutterwave")


def format_amount(amount, currency):
    if currency.upper() in CRYPTO_REGISTRY:
        info = CRYPTO_REGISTRY[currency.upper()]
        decimals = info["decimals"]
        symbol = info["symbol"]
    else:
        info = CURRENCY_REGISTRY.get(currency, {"symbol": currency, "decimals": 2})
        decimals = info["decimals"]
        symbol = info["symbol"]
    formatted = f"{amount:,.{decimals}f}"
    return f"{symbol} {formatted}"


def generate_tx_ref(email, campaign_id="mediagrab"):
    timestamp = int(time.time())
    unique_id = uuid.uuid4().hex[:8]
    email_hash = hashlib.md5(email.lower().encode()).hexdigest()[:6]
    return f"don-{campaign_id}-{email_hash}-{timestamp}-{unique_id}"


_rate_cache = {}


def get_exchange_rate(from_currency, to_currency):
    cache_key = f"{from_currency.lower()}_{to_currency.lower()}"
    now = time.time()
    cached = _rate_cache.get(cache_key)
    if cached and (now - cached[1]) < 60:
        return cached[0]
    try:
        url = f"https://api.coingecko.com/api/v3/simple/price?ids=bitcoin,ethereum,solana,tether,usd-coin&vs_currencies={from_currency.lower()}"
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        crypto_id_map = {"BTC": "bitcoin", "ETH": "ethereum", "SOL": "solana", "USDT": "tether", "USDC": "usd-coin", "DAI": "dai"}
        crypto_id = crypto_id_map.get(to_currency.upper())
        if crypto_id and crypto_id in data:
            rate = data[crypto_id][from_currency.lower()]
            if rate and rate > 0:
                _rate_cache[cache_key] = (rate, now)
                return rate
    except Exception as e:
        logger.warning("Exchange rate fetch failed: %s", str(e))
    if to_currency.upper() in ("USDT", "USDC", "DAI") and from_currency.upper() == "USD":
        return 1.0
    raise PaymentError(f"Could not fetch exchange rate for {from_currency}/{to_currency}", provider="crypto")


def convert_fiat_to_crypto(fiat_amount, fiat_currency, crypto):
    rate = get_exchange_rate(fiat_currency, crypto)
    crypto_amount = Decimal(str(fiat_amount)) / Decimal(str(rate))
    decimals = CRYPTO_REGISTRY.get(crypto.upper(), {"decimals": 8})["decimals"]
    return crypto_amount.quantize(Decimal(f"1e-{decimals}"))


class FlutterwaveProvider:
    BASE_URL = "https://api.flutterwave.com/v3/payments"

    @classmethod
    def create_payment(cls, amount, currency, email, name, tx_ref):
        if not Config.FLW_SECRET_KEY:
            raise RuntimeError("FLW_SECRET_KEY not configured")
        headers = {"Authorization": f"Bearer {Config.FLW_SECRET_KEY}", "Content-Type": "application/json"}
        data = {
            "tx_ref": tx_ref,
            "amount": float(amount),
            "currency": currency,
            "redirect_url": os.getenv("DONATION_REDIRECT_SUCCESS", ""),
            "customer": {"email": email, "name": name},
            "customizations": {"title": f"Donation - {Config.MERCHANT_NAME}", "description": f"MediaGrab donation of {format_amount(amount, currency)}"},
            "meta": {"campaign_id": Config.CAMPAIGN_ID, "donor_name": name},
        }
        try:
            response = requests.post(cls.BASE_URL, json=data, headers=headers, timeout=30)
            response.raise_for_status()
            res = response.json()
        except requests.exceptions.RequestException as e:
            logger.error("Flutterwave API error: %s", str(e), extra={"tx_ref": tx_ref})
            raise PaymentError(f"Payment provider error: {str(e)}", provider="flutterwave")
        if res.get("status") == "success":
            logger.info("Flutterwave payment link created", extra={"tx_ref": tx_ref})
            return {"provider": "flutterwave", "payment_link": res["data"]["link"], "tx_ref": tx_ref, "status": "pending"}
        else:
            raise PaymentError(res.get("message", "Unknown error"), provider="flutterwave")


class StripeProvider:
    BASE_URL = "https://api.stripe.com/v1/payment_links"

    @classmethod
    def create_payment(cls, amount, currency, email, name, tx_ref):
        if not Config.STRIPE_SECRET_KEY:
            raise RuntimeError("STRIPE_SECRET_KEY not configured")
        info = CURRENCY_REGISTRY.get(currency, {"decimals": 2})
        amount_in_cents = int(amount * (10 ** info["decimals"]))
        headers = {"Authorization": f"Bearer {Config.STRIPE_SECRET_KEY}", "Content-Type": "application/x-www-form-urlencoded", "Idempotency-Key": tx_ref}
        price_url = "https://api.stripe.com/v1/prices"
        price_data = {"unit_amount": amount_in_cents, "currency": currency.lower(), "product_data[name]": f"Donation - {Config.MERCHANT_NAME}", "product_data[description]": f"MediaGrab donation from {name}"}
        try:
            price_resp = requests.post(price_url, data=price_data, headers=headers, timeout=30)
            price_resp.raise_for_status()
            price_id = price_resp.json()["id"]
        except requests.exceptions.RequestException as e:
            logger.error("Stripe price creation error: %s", str(e), extra={"tx_ref": tx_ref})
            raise PaymentError(f"Stripe error: {str(e)}", provider="stripe")
        payment_link_data = {"price": price_id, "metadata[campaign_id]": Config.CAMPAIGN_ID, "metadata[tx_ref]": tx_ref, "metadata[donor_name]": name}
        try:
            pl_resp = requests.post(cls.BASE_URL, data=payment_link_data, headers=headers, timeout=30)
            pl_resp.raise_for_status()
            payment_link = pl_resp.json()["url"]
        except requests.exceptions.RequestException as e:
            logger.error("Stripe payment link error: %s", str(e), extra={"tx_ref": tx_ref})
            raise PaymentError(f"Stripe error: {str(e)}", provider="stripe")
        logger.info("Stripe payment link created", extra={"tx_ref": tx_ref})
        return {"provider": "stripe", "payment_link": payment_link, "tx_ref": tx_ref, "status": "pending"}


class NOWPaymentsProvider:
    BASE_URL = "https://api.nowpayments.io/v1"

    @classmethod
    def create_payment(cls, amount, currency, email, name, tx_ref, crypto=None, network=None):
        if not Config.NOWPAYMENTS_API_KEY:
            raise RuntimeError("NOWPAYMENTS_API_KEY not configured")
        headers = {"x-api-key": Config.NOWPAYMENTS_API_KEY, "Content-Type": "application/json"}
        if crypto and crypto.upper() in CRYPTO_REGISTRY:
            crypto_upper = crypto.upper()
            crypto_info = CRYPTO_REGISTRY[crypto_upper]
            if "networks" in crypto_info:
                selected_network = network or crypto_info.get("recommended_network", crypto_info["networks"][0])
                currency_symbol = f"{crypto_upper.lower()}_{selected_network}"
            else:
                selected_network = crypto_info.get("network", "unknown")
                currency_symbol = crypto_upper.lower()
        else:
            crypto_upper = "USDC"
            selected_network = "solana"
            currency_symbol = "usdc_sol"
        fiat_currency = currency if currency in CURRENCY_REGISTRY else "USD"
        try:
            crypto_amount = convert_fiat_to_crypto(amount, fiat_currency, crypto_upper)
        except PaymentError:
            crypto_amount = None
        data = {
            "price_amount": float(amount),
            "price_currency": fiat_currency.lower(),
            "pay_currency": currency_symbol,
            "ipn_callback_url": os.getenv("DONATION_REDIRECT_SUCCESS", ""),
            "order_id": tx_ref,
            "order_description": f"Donation to {Config.MERCHANT_NAME} from {name}",
        }
        if email:
            data["buyer_email"] = email
        try:
            response = requests.post(f"{cls.BASE_URL}/invoice", json=data, headers=headers, timeout=30)
            response.raise_for_status()
            res = response.json()
        except requests.exceptions.RequestException as e:
            logger.error("NOWPayments API error: %s", str(e), extra={"tx_ref": tx_ref})
            raise PaymentError(f"NOWPayments error: {str(e)}", provider="nowpayments")
        if res.get("invoice_id"):
            logger.info("NOWPayments invoice created", extra={"tx_ref": tx_ref})
            return {"provider": "nowpayments", "payment_link": res.get("invoice_url", ""), "tx_ref": tx_ref, "status": "pending", "crypto": crypto_upper, "network": selected_network, "pay_amount": res.get("pay_amount"), "pay_address": res.get("pay_address")}
        raise PaymentError(res.get("message", "NOWPayments invoice creation failed"), provider="nowpayments")


class DirectWalletProvider:
    @classmethod
    def create_payment(cls, amount, currency, email, name, tx_ref, crypto=None, network=None):
        if not crypto:
            crypto = "USDC"
            network = "solana"
        crypto_upper = crypto.upper()
        crypto_info = CRYPTO_REGISTRY.get(crypto_upper)
        if not crypto_info:
            raise PaymentError(f"Unsupported crypto: {crypto}", provider="direct")
        if "networks" in crypto_info:
            selected_network = network or crypto_info.get("recommended_network", crypto_info["networks"][0])
        else:
            selected_network = crypto_info.get("network", "unknown")
        wallet_address = Config.get_wallet_address(crypto_upper)
        if not wallet_address:
            raise PaymentError(f"No wallet address configured for {crypto_upper}. Set WALLET_{crypto_upper} env var.", provider="direct")
        try:
            crypto_amount = convert_fiat_to_crypto(amount, currency if currency in CURRENCY_REGISTRY else "USD", crypto_upper)
        except PaymentError:
            crypto_amount = None
        qr_data = cls._generate_qr_data(wallet_address, crypto_amount, crypto_upper)
        logger.info("Direct wallet payment generated: %s", crypto_upper, extra={"tx_ref": tx_ref})
        return {"provider": "direct", "tx_ref": tx_ref, "status": "pending", "crypto": crypto_upper, "network": selected_network, "wallet_address": wallet_address, "amount": float(crypto_amount) if crypto_amount else None, "formatted_amount": format_amount(crypto_amount, crypto_upper) if crypto_amount else None, "qr_data": qr_data}

    @classmethod
    def _generate_qr_data(cls, address, amount, crypto):
        if amount:
            if crypto.upper() == "BTC":
                return f"bitcoin:{address}?amount={amount}"
            elif crypto.upper() == "SOL":
                return f"solana:{address}?amount={amount}"
            elif crypto.upper() == "ETH":
                return f"ethereum:{address}"
        return address


class DonationPaymentHandler:
    FIAT_PROVIDERS = {"flutterwave": FlutterwaveProvider, "stripe": StripeProvider}
    CRYPTO_PROVIDERS = {"nowpayments": NOWPaymentsProvider, "direct": DirectWalletProvider}

    @classmethod
    def handle(cls, inputs):
        raw_amount = inputs.get("amount")
        if raw_amount is None:
            raise ValidationError("amount is required")
        donor_email = inputs.get("donor_email", "")
        if not donor_email:
            raise ValidationError("donor_email is required")
        donor_name = inputs.get("donor_name", "")
        if not donor_name:
            raise ValidationError("donor_name is required")
        country_code = inputs.get("country_code")
        requested_currency = inputs.get("currency")
        preferred_crypto = inputs.get("crypto") or inputs.get("cryptocurrency")
        preferred_network = inputs.get("network")
        payment_method = inputs.get("payment_method", "")
        email = validate_email(donor_email)
        name = validate_name(donor_name)
        is_crypto = False
        crypto_to_use = preferred_crypto
        if requested_currency and requested_currency.upper() in CRYPTO_REGISTRY:
            is_crypto = True
            crypto_to_use = requested_currency.upper()
        if payment_method and payment_method.lower() in ("crypto", "cryptocurrency", "blockchain"):
            is_crypto = True
        if not Config.CRYPTO_ENABLED:
            is_crypto = False
            crypto_to_use = None
        if is_crypto and crypto_to_use:
            crypto_upper = crypto_to_use.upper()
            if crypto_upper not in CRYPTO_REGISTRY:
                raise ValidationError(f"Unsupported cryptocurrency: {crypto_to_use}")
            amount = validate_amount(raw_amount, "USD")
            try:
                crypto_amount = convert_fiat_to_crypto(amount, "USD", crypto_upper)
            except PaymentError:
                crypto_amount = amount
            tx_ref = generate_tx_ref(email, inputs.get("campaign_id", Config.CAMPAIGN_ID))
            crypto_info = CRYPTO_REGISTRY[crypto_upper]
            logger.info("Processing crypto donation: %s %s", format_amount(amount, "USD"), crypto_upper, extra={"tx_ref": tx_ref})
            for provider_name in Config.CRYPTO_PROVIDER_PRIORITY:
                provider_cls = cls.CRYPTO_PROVIDERS.get(provider_name)
                if not provider_cls:
                    continue
                try:
                    result = provider_cls.create_payment(amount=amount, currency="USD", email=email, name=name, tx_ref=tx_ref, crypto=crypto_upper, network=preferred_network)
                    networks = crypto_info.get("networks", [crypto_info.get("network", "unknown")])
                    return {"status": "success", "payment_type": "crypto", "payment_link": result.get("payment_link", ""), "tx_ref": tx_ref, "provider": provider_name, "crypto": crypto_upper, "crypto_name": crypto_info["name"], "network": result.get("network", networks[0] if isinstance(networks, list) else networks), "amount": float(amount), "fiat_currency": "USD", "crypto_amount": float(result.get("pay_amount", result.get("amount", crypto_amount))), "formatted_amount": format_amount(amount, "USD"), "formatted_crypto": result.get("formatted_amount") or format_amount(crypto_amount, crypto_upper), "currency_symbol": crypto_info["symbol"], "available_networks": networks if isinstance(networks, list) else [networks], "wallet_address": result.get("pay_address") or result.get("wallet_address"), "qr_data": result.get("qr_data"), "donor_email": email, "donor_name": name, "campaign_id": inputs.get("campaign_id", Config.CAMPAIGN_ID), "created_at": datetime.now(timezone.utc).isoformat()}
                except (PaymentError, RuntimeError) as e:
                    logger.warning("%s crypto failed: %s, trying next", provider_name, str(e), extra={"tx_ref": tx_ref})
                    continue
            is_crypto = False
        if not is_crypto:
            currency_for_limits = requested_currency or Config.DEFAULT_CURRENCY
            amount = validate_amount(raw_amount, currency_for_limits)
        else:
            amount = validate_amount(raw_amount, "USD")
        resolved_currency, primary_provider = resolve_currency(country_code, requested_currency if not is_crypto else None)
        formatted_amount = format_amount(amount, resolved_currency)
        tx_ref = generate_tx_ref(email, inputs.get("campaign_id", Config.CAMPAIGN_ID))
        logger.info("Processing donation: %s via %s", formatted_amount, primary_provider, extra={"tx_ref": tx_ref})
        for provider_name in cls.FIAT_PROVIDERS:
            provider_cls = cls.FIAT_PROVIDERS[provider_name]
            try:
                result = provider_cls.create_payment(amount=amount, currency=resolved_currency, email=email, name=name, tx_ref=tx_ref)
                logger.info("Payment successful via %s", provider_name, extra={"tx_ref": tx_ref})
                return {"status": "success", "payment_type": "fiat", "payment_link": result["payment_link"], "tx_ref": tx_ref, "provider": provider_name, "amount": float(amount), "currency": resolved_currency, "formatted_amount": formatted_amount, "currency_symbol": CURRENCY_REGISTRY.get(resolved_currency, {}).get("symbol", resolved_currency), "donor_email": email, "donor_name": name, "campaign_id": inputs.get("campaign_id", Config.CAMPAIGN_ID), "created_at": datetime.now(timezone.utc).isoformat()}
            except (PaymentError, RuntimeError) as e:
                logger.warning("%s failed: %s, trying next provider", provider_name, str(e), extra={"tx_ref": tx_ref})
                continue
        logger.error("All payment providers failed", extra={"tx_ref": tx_ref})
        return {"status": "failed", "payment_link": "", "tx_ref": tx_ref, "error": "All payment providers failed", "formatted_amount": formatted_amount, "currency": resolved_currency}

    @classmethod
    def get_supported_cryptos(cls):
        result = []
        for symbol, info in CRYPTO_REGISTRY.items():
            result.append({"symbol": symbol, "name": info["name"], "symbol_char": info["symbol"], "networks": info.get("networks", [info.get("network", "unknown")]), "type": info["type"], "is_stablecoin": info["type"] == "stablecoin"})
        return result


def handler(inputs):
    try:
        missing = Config.validate()
        if missing:
            logger.error("Missing required env vars: %s", ", ".join(missing))
            return {"status": "error", "error": f"Missing required environment variables: {', '.join(missing)}", "payment_link": ""}
        result = DonationPaymentHandler.handle(inputs)
        return result
    except ValidationError as e:
        logger.warning("Validation error: %s", str(e))
        return {"status": "validation_error", "error": str(e), "payment_link": ""}
    except Exception as e:
        logger.error("Unexpected error: %s", str(e), exc_info=True)
        return {"status": "error", "error": "An unexpected error occurred. Please try again.", "payment_link": ""}
