"""Replicate video generation backend.

Wraps Replicate's official video models (Veo 3, Veo 3 Fast, Kling v2.1,
Hailuo 02, Seedance 1 Pro) as a :class:`VideoGenProvider`. Text-to-video
by default; when ``image_url`` is provided and the model supports it, an
``image``/``start_image`` input is added for image-to-video. Talks to the
Replicate HTTP API directly (create prediction + poll) via the stdlib.

Model selection precedence:
    1. ``model=`` arg from the tool call
    2. ``REPLICATE_VIDEO_MODEL`` env var
    3. ``video_gen.replicate.model`` in config.yaml
    4. ``video_gen.model`` in config.yaml (when it's one of our ids)
    5. ``DEFAULT_MODEL``

Auth: ``REPLICATE_API_TOKEN`` (env or HERMES_HOME/.env).
"""

from __future__ import annotations

import json
import logging
import os
import time
import urllib.request
from typing import Any, Dict, List, Optional

from agent.video_gen_provider import (
    DEFAULT_ASPECT_RATIO,
    VideoGenProvider,
    error_response,
    success_response,
)

logger = logging.getLogger(__name__)

DEFAULT_MODEL = "google/veo-3"

# Catalog. `image_key` names the model's image-to-video input field (None =
# text-to-video only). `audio` marks native audio support.
MODELS: Dict[str, Dict[str, Any]] = {
    "google/veo-3": {
        "display": "Veo 3", "speed": "~2-4min", "price": "premium", "tier": "premium",
        "strengths": "Google DeepMind flagship — cinematic, native audio, top prompt adherence.",
        "image_key": "image", "audio": True,
    },
    "google/veo-3-fast": {
        "display": "Veo 3 Fast", "speed": "~1-2min", "price": "premium", "tier": "premium",
        "strengths": "Faster, cheaper Veo 3 with native audio.",
        "image_key": "image", "audio": True,
    },
    "kwaivgi/kling-v2.1": {
        "display": "Kling v2.1", "speed": "~2-5min", "price": "premium", "tier": "premium",
        "strengths": "Strong motion and realism, image-to-video.",
        "image_key": "start_image", "audio": False,
    },
    "minimax/hailuo-02": {
        "display": "Hailuo 02", "speed": "~2-4min", "price": "premium", "tier": "premium",
        "strengths": "Great physics and camera control.",
        "image_key": "first_frame_image", "audio": False,
    },
    "bytedance/seedance-1-pro": {
        "display": "Seedance 1 Pro", "speed": "~2-4min", "price": "premium", "tier": "premium",
        "strengths": "Cinematic multi-shot, 1080p.",
        "image_key": "image", "audio": False,
    },
}

_API_ROOT = "https://api.replicate.com/v1"
_POLL_TIMEOUT = 600   # seconds — video renders can take minutes
_POLL_INTERVAL = 5


def _get_token() -> str:
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


def _resolve_model(explicit: Optional[str]) -> str:
    candidates: List[Optional[str]] = [explicit, os.environ.get("REPLICATE_VIDEO_MODEL")]
    try:
        from hermes_cli.config import load_config
        cfg = load_config() or {}
        sec = cfg.get("video_gen") if isinstance(cfg, dict) else {}
        sec = sec if isinstance(sec, dict) else {}
        rep = sec.get("replicate") if isinstance(sec.get("replicate"), dict) else {}
        candidates.append(rep.get("model"))
        candidates.append(sec.get("model"))
    except Exception:
        pass
    for c in candidates:
        if isinstance(c, str) and c.strip() in MODELS:
            return c.strip()
    return DEFAULT_MODEL


def _run_replicate(model: str, payload: Dict[str, Any], token: str) -> Dict[str, Any]:
    body = json.dumps({"input": payload}).encode("utf-8")
    req = urllib.request.Request(
        f"{_API_ROOT}/models/{model}/predictions",
        data=body, method="POST",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Prefer": "wait",
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
    if isinstance(output, dict):
        for k in ("video", "url", "output"):
            v = output.get(k)
            if isinstance(v, str):
                return v
    return None


class ReplicateVideoGenProvider(VideoGenProvider):
    @property
    def name(self) -> str:
        return "replicate"

    @property
    def display_name(self) -> str:
        return "Replicate"

    def is_available(self) -> bool:
        return bool(_get_token())

    def list_models(self) -> List[Dict[str, Any]]:
        out: List[Dict[str, Any]] = []
        for mid, m in MODELS.items():
            modalities = ["text"] + (["image"] if m.get("image_key") else [])
            out.append({"id": mid, "display": m["display"], "speed": m["speed"],
                        "strengths": m["strengths"], "price": m["price"],
                        "tier": m["tier"], "modalities": modalities})
        return out

    def default_model(self) -> Optional[str]:
        return DEFAULT_MODEL

    def capabilities(self) -> Dict[str, Any]:
        return {
            "modalities": ["text", "image"],
            "aspect_ratios": ["16:9", "9:16", "1:1"],
            "resolutions": ["720p", "1080p"],
            "max_duration": 8,
            "min_duration": 4,
            "supports_audio": True,
            "supports_negative_prompt": True,
            "max_reference_images": 0,
        }

    def get_setup_schema(self) -> Dict[str, Any]:
        return {
            "name": "Replicate",
            "badge": "paid",
            "tag": "Veo 3, Veo 3 Fast, Kling v2.1, Hailuo 02, Seedance 1 Pro — text & image to video",
            "env_vars": [
                {"key": "REPLICATE_API_TOKEN",
                 "prompt": "Replicate API token",
                 "url": "https://replicate.com/account/api-tokens"},
            ],
        }

    def generate(
        self,
        prompt: str,
        *,
        model: Optional[str] = None,
        image_url: Optional[str] = None,
        reference_image_urls: Optional[List[str]] = None,
        duration: Optional[int] = None,
        aspect_ratio: str = DEFAULT_ASPECT_RATIO,
        resolution: str = "720p",
        negative_prompt: Optional[str] = None,
        audio: Optional[bool] = None,
        seed: Optional[int] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        model_id = _resolve_model(model)
        meta = MODELS[model_id]
        token = _get_token()
        prompt = (prompt or "").strip()

        if not token:
            return error_response(
                error="REPLICATE_API_TOKEN is not set",
                error_type="auth_required", provider="replicate",
                model=model_id, prompt=prompt)
        if not prompt:
            return error_response(
                error="prompt is required", error_type="missing_prompt",
                provider="replicate", model=model_id, prompt=prompt)

        payload: Dict[str, Any] = {"prompt": prompt}
        if aspect_ratio in ("16:9", "9:16", "1:1"):
            payload["aspect_ratio"] = aspect_ratio
        if negative_prompt:
            payload["negative_prompt"] = negative_prompt
        if seed is not None:
            payload["seed"] = seed

        image_url_norm = (image_url or "").strip() or None
        modality = "text"
        if image_url_norm and meta.get("image_key"):
            payload[meta["image_key"]] = image_url_norm
            modality = "image"

        try:
            pred = _run_replicate(model_id, payload, token)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Replicate video gen failed (%s): %s", model_id, exc, exc_info=True)
            return error_response(
                error=f"Replicate request failed: {exc}",
                error_type="api_error", provider="replicate",
                model=model_id, prompt=prompt, aspect_ratio=aspect_ratio)

        if pred.get("status") != "succeeded":
            return error_response(
                error=f"Replicate prediction {pred.get('status')}: "
                      f"{pred.get('error') or 'no output'}",
                error_type="provider_error", provider="replicate",
                model=model_id, prompt=prompt)

        url = _first_url(pred.get("output"))
        if not url:
            return error_response(
                error="Replicate returned no video URL",
                error_type="empty_response", provider="replicate",
                model=model_id, prompt=prompt)

        return success_response(
            video=url, model=model_id, prompt=prompt, modality=modality,
            aspect_ratio=aspect_ratio if "aspect_ratio" in payload else "",
            duration=duration or 0, provider="replicate",
            extra={"prediction_id": pred.get("id")})


def register(ctx) -> None:
    """Plugin entry point — wire ``ReplicateVideoGenProvider`` into the registry."""
    ctx.register_video_gen_provider(ReplicateVideoGenProvider())
