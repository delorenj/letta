"""FastAPI application for Anthropic MAX OAuth proxy."""

import json
import logging
from contextlib import asynccontextmanager

import httpx
import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, StreamingResponse

from .config import settings
from .oauth import token_manager
from .translator import (
    MODEL_MAP,
    anthropic_stream_to_openai_stream,
    anthropic_to_openai_response,
    openai_to_anthropic_request,
    translate_model,
)

# Configure logging
logging.basicConfig(level=getattr(logging, settings.log_level))
logger = logging.getLogger(__name__)

# Anthropic beta headers required for OAuth
ANTHROPIC_BETAS = [
    "oauth-2025-04-20",
    "claude-code-20250219",
    "interleaved-thinking-2025-05-14",
    "fine-grained-tool-streaming-2025-05-14",
]


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    # Check auth status on startup
    if token_manager.is_authenticated():
        logger.info("Anthropic MAX OAuth tokens loaded")
    else:
        logger.warning(
            "No Anthropic MAX tokens found. "
            "Visit /auth/start to begin OAuth flow."
        )
    yield


app = FastAPI(
    title="Anthropic MAX OAuth Proxy",
    description="OpenAI-compatible proxy for Anthropic MAX subscription",
    version="0.1.0",
    lifespan=lifespan,
)


# ============================================================================
# Health & Status
# ============================================================================


@app.get("/health")
@app.get("/v1/health")
async def health():
    """Health check endpoint."""
    return {
        "status": "ok",
        "authenticated": token_manager.is_authenticated(),
    }


@app.get("/auth/status")
async def auth_status():
    """Check authentication status."""
    tokens = token_manager.load()
    if not tokens:
        return {"authenticated": False, "message": "No tokens found. Visit /auth/start to authenticate."}

    return {
        "authenticated": True,
        "expires_at": tokens.expires_at,
        "is_expired": tokens.is_expired(),
    }


# ============================================================================
# OAuth Flow
# ============================================================================


@app.get("/auth/start")
async def auth_start():
    """Start OAuth flow - returns URL to visit."""
    url, verifier = token_manager.start_auth_flow()
    return {
        "message": "Visit the URL below and authenticate with your Anthropic account",
        "url": url,
        "verifier": verifier,
        "next_step": f"After authenticating, copy the code and POST to /auth/callback with the code",
    }


@app.post("/auth/callback")
async def auth_callback(request: Request):
    """Complete OAuth flow with authorization code."""
    body = await request.json()
    code = body.get("code")
    verifier = body.get("verifier")  # Optional if stored from /auth/start

    if not code:
        raise HTTPException(status_code=400, detail="Missing 'code' in request body")

    success = await token_manager.complete_auth_flow(code, verifier)
    if success:
        return {"status": "success", "message": "Authentication complete!"}
    else:
        raise HTTPException(status_code=400, detail="Failed to exchange code for tokens")


@app.post("/auth/logout")
async def auth_logout():
    """Clear stored tokens."""
    token_manager.clear()
    return {"status": "success", "message": "Tokens cleared"}


# ============================================================================
# OpenAI-Compatible API
# ============================================================================


@app.get("/v1/models")
async def list_models():
    """List available models (OpenAI format)."""
    models = []
    for openai_name, anthropic_id in MODEL_MAP.items():
        models.append({
            "id": openai_name,
            "object": "model",
            "created": 1700000000,
            "owned_by": "anthropic",
            "anthropic_id": anthropic_id,
        })

    return {"object": "list", "data": models}


@app.post("/v1/chat/completions")
async def chat_completions(request: Request):
    """
    OpenAI-compatible chat completions endpoint.
    Translates to Anthropic API and proxies the request.
    """
    # Check authentication
    access_token = await token_manager.get_valid_token()
    if not access_token:
        raise HTTPException(
            status_code=401,
            detail="Not authenticated. Visit /auth/start to authenticate with Anthropic MAX."
        )

    # Parse OpenAI request
    openai_request = await request.json()
    logger.debug(f"OpenAI request: {json.dumps(openai_request, indent=2)}")

    # Translate to Anthropic format
    anthropic_request = openai_to_anthropic_request(openai_request)
    original_model = openai_request.get("model", "")
    logger.debug(f"Anthropic request: {json.dumps(anthropic_request, indent=2)}")

    # Build headers for Anthropic
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        "anthropic-version": "2023-06-01",
        "anthropic-beta": ",".join(ANTHROPIC_BETAS),
    }

    # Handle streaming vs non-streaming
    if openai_request.get("stream"):
        return await _handle_streaming(anthropic_request, headers, original_model)
    else:
        return await _handle_non_streaming(anthropic_request, headers, original_model)


async def _handle_non_streaming(
    anthropic_request: dict, headers: dict, original_model: str
) -> JSONResponse:
    """Handle non-streaming request."""
    async with httpx.AsyncClient(timeout=120.0) as client:
        response = await client.post(
            f"{settings.anthropic_api_url}/messages",
            json=anthropic_request,
            headers=headers,
        )

        if not response.is_success:
            logger.error(f"Anthropic error: {response.status_code} - {response.text}")
            raise HTTPException(
                status_code=response.status_code,
                detail=f"Anthropic API error: {response.text}",
            )

        anthropic_response = response.json()
        logger.debug(f"Anthropic response: {json.dumps(anthropic_response, indent=2)}")

        # Translate back to OpenAI format
        openai_response = anthropic_to_openai_response(anthropic_response, original_model)
        return JSONResponse(content=openai_response)


async def _handle_streaming(
    anthropic_request: dict, headers: dict, original_model: str
) -> StreamingResponse:
    """Handle streaming request."""

    async def generate():
        async with httpx.AsyncClient(timeout=120.0) as client:
            async with client.stream(
                "POST",
                f"{settings.anthropic_api_url}/messages",
                json=anthropic_request,
                headers=headers,
            ) as response:
                if not response.is_success:
                    error_text = await response.aread()
                    logger.error(f"Anthropic stream error: {response.status_code} - {error_text}")
                    yield f"data: {json.dumps({'error': error_text.decode()})}\n\n"
                    return

                async for line in response.aiter_lines():
                    if not line:
                        continue

                    # Parse SSE format
                    if line.startswith("event: "):
                        event_type = line[7:]
                    elif line.startswith("data: "):
                        try:
                            data = json.loads(line[6:])
                            openai_chunk = anthropic_stream_to_openai_stream(
                                event_type, data, original_model
                            )
                            if openai_chunk:
                                yield f"data: {json.dumps(openai_chunk)}\n\n"
                        except json.JSONDecodeError:
                            continue

                # Send [DONE] marker
                yield "data: [DONE]\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )


# ============================================================================
# Entry Point
# ============================================================================


def run():
    """Run the proxy server."""
    uvicorn.run(
        "anthropic_max_proxy.main:app",
        host=settings.host,
        port=settings.port,
        reload=False,
        log_level=settings.log_level.lower(),
    )


if __name__ == "__main__":
    run()
