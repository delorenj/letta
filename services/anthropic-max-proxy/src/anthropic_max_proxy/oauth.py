"""OAuth 2.0 PKCE flow for Anthropic MAX subscription."""

import base64
import hashlib
import json
import secrets
import time
from dataclasses import dataclass
from pathlib import Path

import httpx

from .config import settings


@dataclass
class PKCEChallenge:
    """PKCE challenge/verifier pair."""

    verifier: str
    challenge: str


@dataclass
class OAuthTokens:
    """OAuth token storage."""

    access_token: str
    refresh_token: str
    expires_at: float  # Unix timestamp

    def is_expired(self, buffer_seconds: int = 60) -> bool:
        """Check if token is expired (with buffer)."""
        return time.time() >= (self.expires_at - buffer_seconds)

    def to_dict(self) -> dict:
        return {
            "access_token": self.access_token,
            "refresh_token": self.refresh_token,
            "expires_at": self.expires_at,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "OAuthTokens":
        return cls(
            access_token=data["access_token"],
            refresh_token=data["refresh_token"],
            expires_at=data["expires_at"],
        )


def generate_pkce() -> PKCEChallenge:
    """Generate PKCE verifier and challenge."""
    # 32 bytes = 256 bits of entropy
    verifier = secrets.token_urlsafe(32)

    # SHA256 hash, base64url encoded (no padding)
    digest = hashlib.sha256(verifier.encode()).digest()
    challenge = base64.urlsafe_b64encode(digest).decode().rstrip("=")

    return PKCEChallenge(verifier=verifier, challenge=challenge)


def build_auth_url(pkce: PKCEChallenge) -> str:
    """Build Anthropic OAuth authorization URL."""
    params = {
        "code": "true",
        "client_id": settings.anthropic_client_id,
        "response_type": "code",
        "redirect_uri": "https://console.anthropic.com/oauth/code/callback",
        "scope": "org:create_api_key user:profile user:inference",
        "code_challenge": pkce.challenge,
        "code_challenge_method": "S256",
        "state": pkce.verifier,  # Store verifier in state for later use
    }

    query = "&".join(f"{k}={v}" for k, v in params.items())
    return f"{settings.anthropic_oauth_url}?{query}"


async def exchange_code(code: str, verifier: str) -> OAuthTokens | None:
    """Exchange authorization code for tokens."""
    # Code format from Anthropic: "actual_code#state"
    splits = code.split("#")
    actual_code = splits[0]
    state = splits[1] if len(splits) > 1 else ""

    async with httpx.AsyncClient() as client:
        response = await client.post(
            settings.anthropic_token_url,
            json={
                "code": actual_code,
                "state": state,
                "grant_type": "authorization_code",
                "client_id": settings.anthropic_client_id,
                "redirect_uri": "https://console.anthropic.com/oauth/code/callback",
                "code_verifier": verifier,
            },
            headers={"Content-Type": "application/json"},
        )

        if not response.is_success:
            return None

        data = response.json()
        return OAuthTokens(
            access_token=data["access_token"],
            refresh_token=data["refresh_token"],
            expires_at=time.time() + data["expires_in"],
        )


async def refresh_tokens(refresh_token: str) -> OAuthTokens | None:
    """Refresh access token using refresh token."""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            settings.anthropic_token_url,
            json={
                "grant_type": "refresh_token",
                "refresh_token": refresh_token,
                "client_id": settings.anthropic_client_id,
            },
            headers={"Content-Type": "application/json"},
        )

        if not response.is_success:
            return None

        data = response.json()
        return OAuthTokens(
            access_token=data["access_token"],
            refresh_token=data["refresh_token"],
            expires_at=time.time() + data["expires_in"],
        )


class TokenManager:
    """Manage OAuth token storage and refresh."""

    def __init__(self, token_file: Path | None = None):
        self.token_file = token_file or settings.token_file
        self._tokens: OAuthTokens | None = None
        self._pkce: PKCEChallenge | None = None

    def _ensure_dir(self) -> None:
        """Ensure token directory exists."""
        self.token_file.parent.mkdir(parents=True, exist_ok=True)

    def load(self) -> OAuthTokens | None:
        """Load tokens from file."""
        if self._tokens:
            return self._tokens

        if self.token_file.exists():
            try:
                data = json.loads(self.token_file.read_text())
                self._tokens = OAuthTokens.from_dict(data)
                return self._tokens
            except (json.JSONDecodeError, KeyError):
                return None
        return None

    def save(self, tokens: OAuthTokens) -> None:
        """Save tokens to file."""
        self._ensure_dir()
        self._tokens = tokens
        self.token_file.write_text(json.dumps(tokens.to_dict(), indent=2))
        # Restrict permissions
        self.token_file.chmod(0o600)

    def clear(self) -> None:
        """Clear stored tokens."""
        self._tokens = None
        if self.token_file.exists():
            self.token_file.unlink()

    def start_auth_flow(self) -> tuple[str, str]:
        """Start OAuth flow, return (auth_url, verifier)."""
        self._pkce = generate_pkce()
        url = build_auth_url(self._pkce)
        return url, self._pkce.verifier

    async def complete_auth_flow(self, code: str, verifier: str | None = None) -> bool:
        """Complete OAuth flow with authorization code."""
        # Use stored verifier if not provided
        v = verifier or (self._pkce.verifier if self._pkce else None)
        if not v:
            return False

        tokens = await exchange_code(code, v)
        if tokens:
            self.save(tokens)
            self._pkce = None
            return True
        return False

    async def get_valid_token(self) -> str | None:
        """Get valid access token, refreshing if needed."""
        tokens = self.load()
        if not tokens:
            return None

        # Refresh if expired
        if tokens.is_expired():
            new_tokens = await refresh_tokens(tokens.refresh_token)
            if new_tokens:
                self.save(new_tokens)
                tokens = new_tokens
            else:
                # Refresh failed, need to re-auth
                self.clear()
                return None

        return tokens.access_token

    def is_authenticated(self) -> bool:
        """Check if we have stored tokens."""
        return self.load() is not None


# Global token manager instance
token_manager = TokenManager()
