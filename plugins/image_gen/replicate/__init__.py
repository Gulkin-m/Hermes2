"""Replicate image generation backend.

Wraps Replicate's official image models (Imagen 4 Ultra, FLUX 1.1 Pro
Ultra, Ideogram v3, Recraft v3) as an :class:`ImageGenProvider`. Talks to
the Replicate HTTP API directly (create prediction + poll) with the
stdlib so it carries no extra dependency.

Model selection precedence:
    1. ``image_gen.replicate.model`` in config.yaml
    2. ``image_gen.model`` in config.yaml (when it's one of our ids)
    3. ``DEFAULT_MODEL``

Auth: ``REPLICATE_API_TOKEN`` (env or HERMES_HOME/.env).
"""

from __future__ import annotations

import json
import logging
import os
import time
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional

from agent.image_gen_provider import (
    DEFAULT_ASPECT_RATIO,
    ImageGenProvider,
    resolve_aspect_ratio,
)

logger = logging.getLogger(__name__)

DEFAULT_MODEL = "google/imagen-4-ultra"

# Catalog surfaced in `hermes tools`. Default first.
MODELS: Dict[str, Dict[str, str]] = {
    "google/imagen-4-ultra": {
        "display": "Imagen 4 Ultra",
        "strengths": "Google's top text-to-image — photoreal, best prompt adherence.",
        "price": "premium",
    },
    "black-forest-labs/flux-1.1-pro-ultra": {
        "display": "FLUX 1.1 Pro Ultra",
        "strengths": "Up to 4MP, superb detail and composition.",
        "price": "premium",
    },
    "ideogram-ai/ideogram-v3-quality": {
        "display": "Ideogram v3 Quality",
        "strengths": "Best-in-class text rendering inside images.",
        "price": "premium",
    },
    "recraft-ai/recraft-v3": {
        "display": "Recraft v3",
        "strengths": "Brand/vector/logo work, style control.",
        "price": "premium",
    },
}

# Hermes uses word aspect ratios; Replicate models want numeric ratios.
_ASPECT_MAP = {"landscape": "16:9", "square": "1:1", "portrait": "9:16"}

_API_ROOT = "https://api.replicate.com/v1"
_POLL_TIMEOUT = 120   # seconds — images finish well within this
_POLL_INTERVAL = 2


def _get_token() -> str:
    """REPLICATE_API_TOKEN from the process env, falling back to .env."""
    tok = os.environ.get("REPLICATE_API_TOKEN", "").strip()
    if tok:
        return tok
    try:
        from hermes_constants import get_hermes_home
        for line in (get_hermes_home() / ".env").read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line.startswith("REPLICATE_API_TOKEN=") and "=" in line:
                return line.partition("=")[2].strip()
    except Exception:
        pass
    return ""


def _resolve_model() -> str:
    try:
        from hermes_cli.config import load_config
        cfg = load_config() or {}
        sec = cfg.get("image_gen") if isinstance(cfg, dict) else {}
        sec = sec if isinstance(sec, dict) else {}
        rep = sec.get("replicate") if isinstance(sec.get("replicate"), dict) else {}
        for cand in (rep.get("model"), sec.get("model")):
            if isinstance(cand, str) and cand.strip():
                return cand.strip()
    except Exception:
        pass
    return DEFAULT_MODEL


def _run_replicate(model: str, payload: Dict[str, Any], token: str) -> Dict[str, Any]:
    """Create a prediction and block until it finishes. Returns the raw
    prediction dict, or raises on transport/timeout error."""
    body = json.dumps({"input": payload}).encode("utf-8")
    req = urllib.request.Request(
        f"{_API_ROOT}/models/{model}/predictions",
        data=body, method="POST",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Prefer": "wait",  # block up to ~60s server-side before returning
        },
    )
    with urllib.request.urlopen(req, timeout=90) as resp:
        pred = json.loads(resp.read().decode("utf-8", "replace"))

    deadline = time.time() + _POLL_TIMEOUT
    while pred.get("status") not in ("succeeded", "failed", "canceled"):
        if time.time() > deadline:
            raise TimeoutError(f"prediction timed out after {_POLL_TIMEOUT}s")
        time.sleep(_POLL_INTERVAL)
        get_url = (pred.get("urls") or {}).get("get")
        if not get_url:
            break
        r = urllib.request.Request(get_url, headers={"Authorization": f"Bearer {token}"})
        with urllib.request.urlopen(r, timeout=30) as resp:
            pred = json.loads(resp.read().decode("utf-8", "replace"))
    return pred


def _first_url(output: Any) -> Optional[str]:
    if isinstance(output, str):
        return output
    if isinstance(output, list) and output:
        first = output[0]
        return first if isinstance(first, str) else None
    return None


class ReplicateImageGenProvider(ImageGenProvider):
    @property
    def name(self) -> str:
        return "replicate"

    @property
    def display_name(self) -> str:
        return "Replicate"

    def is_available(self) -> bool:
        return bool(_get_token())

    def list_models(self) -> List[Dict[str, Any]]:
        return [{"id": mid, "display": m["display"],
                 "strengths": m["strengths"], "price": m["price"]}
                for mid, m in MODELS.items()]

    def default_model(self) -> Optional[str]:
        return DEFAULT_MODEL

    def get_setup_schema(self) -> Dict[str, Any]:
        return {
            "name": "Replicate",
            "badge": "paid",
            "tag": "Imagen 4 Ultra, FLUX 1.1 Pro Ultra, Ideogram v3, Recraft v3",
            "env_vars": [
                {"key": "REPLICATE_API_TOKEN",
                 "prompt": "Replicate API token",
                 "url": "https://replicate.com/account/api-tokens"},
            ],
        }

    def generate(
        self,
        prompt: str,
        aspect_ratio: str = DEFAULT_ASPECT_RATIO,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        aspect = resolve_aspect_ratio(aspect_ratio)
        model = _resolve_model()
        token = _get_token()
        base = {"success": False, "image": None, "provider": "replicate",
                "model": model, "prompt": prompt, "aspect_ratio": aspect}

        if not token:
            return {**base, "error": "REPLICATE_API_TOKEN is not set",
                    "error_type": "auth_required"}
        if not (prompt or "").strip():
            return {**base, "error": "prompt is required",
                    "error_type": "missing_prompt"}

        payload: Dict[str, Any] = {"prompt": prompt.strip()}
        ratio = _ASPECT_MAP.get(aspect)
        if ratio:
            payload["aspect_ratio"] = ratio
        if kwargs.get("seed") is not None:
            payload["seed"] = kwargs["seed"]

        try:
            pred = _run_replicate(model, payload, token)
        except Exception as exc:  # noqa: BLE001 — never raise out of generate
            logger.warning("Replicate image gen failed (%s): %s", model, exc, exc_info=True)
            return {**base, "error": f"Replicate request failed: {exc}",
                    "error_type": type(exc).__name__}

        if pred.get("status") != "succeeded":
            return {**base,
                    "error": f"Replicate prediction {pred.get('status')}: "
                             f"{pred.get('error') or 'no output'}",
                    "error_type": "provider_error"}

        url = _first_url(pred.get("output"))
        if not url:
            return {**base, "error": "Replicate returned no image URL",
                    "error_type": "empty_response"}

        return {"success": True, "image": url, "provider": "replicate",
                "model": model, "prompt": prompt.strip(), "aspect_ratio": aspect,
                "prediction_id": pred.get("id")}


def register(ctx) -> None:
    """Plugin entry point — wire ``ReplicateImageGenProvider`` into the registry."""
    ctx.register_image_gen_provider(ReplicateImageGenProvider())
