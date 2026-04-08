"""
MediaGrab - Shared Platform Detection Module
Centralized platform patterns and detection logic for all components.
"""

from typing import Dict, List
from urllib.parse import urlparse

# Platform patterns used across desktop, backend, and mobile
PLATFORM_PATTERNS: Dict[str, List[str]] = {
    "youtube":     ["youtube.com", "youtu.be", "music.youtube.com"],
    "vimeo":       ["vimeo.com"],
    "tiktok":      ["tiktok.com", "vm.tiktok.com", "vt.tiktok.com"],
    "instagram":   ["instagram.com", "instagr.am"],
    "facebook":    ["facebook.com", "fb.watch"],
    "twitter":     ["twitter.com", "x.com"],
    "reddit":      ["reddit.com", "v.redd.it"],
    "dailymotion": ["dailymotion.com", "dai.ly"],
    "twitch":      ["twitch.tv"],
}

SUPPORTED_PLATFORMS = (
    "YouTube & YouTube Music",
    "TikTok", 
    "Instagram",
    "Facebook",
    "Twitter/X",
    "Vimeo",
    "Reddit",
    "Dailymotion",
    "Twitch",
    "Direct HTTP video links",
)


def detect_platform(url: str) -> str:
    """
    Detect platform from URL.
    Returns platform name or "generic_http" for direct links.
    """
    try:
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        
        for platform, domains in PLATFORM_PATTERNS.items():
            if any(d in domain for d in domains):
                return platform
                
        # Check if it's a direct HTTP link
        if parsed.scheme in ("http", "https") and domain:
            return "generic_http"
            
        return "unknown"
    except Exception:
        return "unknown"


def validate_url(url: str) -> bool:
    """
    Basic URL validation.
    """
    try:
        r = urlparse(url)
        return r.scheme in ("http", "https") and bool(r.netloc)
    except Exception:
        return False


def get_supported_platforms() -> tuple:
    """Get tuple of supported platform names."""
    return SUPPORTED_PLATFORMS


def get_platform_patterns() -> Dict[str, List[str]]:
    """Get platform patterns dictionary."""
    return PLATFORM_PATTERNS
