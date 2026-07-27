"""
Gateway startup self-test hook.

Fires on ``gateway:startup``. Reads the LIVE orchestration wiring from
config.yaml (main model, delegation, vision aux, fallback) and pings each real
endpoint, plus the providers (Perplexity, OpenRouter) and MCP servers (GitHub,
Firecrawl). Posts a compact report card to the Telegram home channel.

Every check is best-effort and fully guarded: a failing probe shows a red mark
but never raises, so the hook can never block or crash gateway startup.

Config knobs (env / .env, all optional):
  SELFTEST_DISABLE=1        -- skip the self-test entirely
  SELFTEST_CHAT_ID=<id>     -- override the destination chat (default:
                               TELEGRAM_HOME_CHANNEL)
"""

from __future__ import annotations

import asyncio
import json
import re
import urllib.request
import urllib.parse
from typing import Optional, Tuple

import yaml

from hermes_cli.config import get_hermes_home

HOME = get_hermes_home()
ENV_PATH = HOME / ".env"
AGENT_LOG = HOME / "logs" / "agent.log"
CONFIG_PATH = HOME / "config.yaml"
SOUL_PATH = HOME / "SOUL.md"
HTTP_TIMEOUT = 12


# ---------------------------------------------------------------- env / config

def _load_env() -> dict:
    """Parse HERMES_HOME/.env into a dict (independent of os.environ)."""
    env: dict = {}
    try:
        for line in ENV_PATH.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, _, v = line.partition("=")
            env[k.strip()] = v.strip()
    except Exception:
        pass
    return env


def _load_config() -> dict:
    try:
        return yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8")) or {}
    except Exception:
        return {}


def _http(method: str, url: str, headers: dict | None = None,
          body: dict | None = None) -> Tuple[int, str]:
    """Blocking HTTP call. Returns (status_code, text). Never raises."""
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(url, data=data, method=method,
                                 headers=headers or {})
    try:
        with urllib.request.urlopen(req, timeout=HTTP_TIMEOUT) as resp:
            return resp.status, resp.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        try:
            return e.code, e.read().decode("utf-8", "replace")
        except Exception:
            return e.code, ""
    except Exception as e:
        return 0, str(e)


# ------------------------------------------------------------- model pinging

# Provider -> (endpoint, api-key env var). Direct provider hosts only; anything
# else is reported as "не проверяется" rather than guessed.
_PROVIDER_ENDPOINTS = {
    "openrouter": ("https://openrouter.ai/api/v1/chat/completions", "OPENROUTER_API_KEY"),
    "deepseek":   ("https://api.deepseek.com/chat/completions",     "DEEPSEEK_API_KEY"),
    "perplexity": ("https://api.perplexity.ai/chat/completions",    "PERPLEXITY_API_KEY"),
}


def _ping_model(env: dict, provider: str, model: str) -> Tuple[bool, str]:
    """Send a minimal completion to (provider, model). Returns (ok, detail)."""
    provider = (provider or "").strip().lower()
    model = (model or "").strip()
    if not model:
        return False, "не задана"
    ep = _PROVIDER_ENDPOINTS.get(provider)
    if not ep:
        return False, f"провайдер '{provider}' не проверяется"
    url, key_var = ep
    key = env.get(key_var, "")
    if not key:
        return False, f"нет ключа ({key_var})"
    body = {"model": model,
            "messages": [{"role": "user", "content": "Reply with just: ok"}]}
    # Perplexity search models reject very small max_tokens; others are fine
    # with a tight cap to keep the ping cheap.
    if provider != "perplexity":
        body["max_tokens"] = 5
    code, _ = _http("POST", url,
                    {"Authorization": f"Bearer {key}",
                     "Content-Type": "application/json"}, body)
    return code == 200, ("отвечает" if code == 200 else f"HTTP {code}")


# --------------------------------------------------------------- other probes

def _check_openrouter(env: dict) -> Tuple[bool, str]:
    key = env.get("OPENROUTER_API_KEY", "")
    if not key:
        return False, "нет ключа"
    hdr = {"Authorization": f"Bearer {key}"}
    mcode, mtext = _http("GET", "https://openrouter.ai/api/v1/models", hdr)
    _, ctext = _http("GET", "https://openrouter.ai/api/v1/credits", hdr)
    if mcode != 200:
        return False, f"HTTP {mcode}"
    n_models = mtext.count('"id"')
    bal = ""
    try:
        d = json.loads(ctext).get("data", {})
        rem = float(d.get("total_credits", 0)) - float(d.get("total_usage", 0))
        bal = f", ~{rem:.2f} USD"
    except Exception:
        pass
    return True, f"{n_models} моделей{bal}"


def _check_firecrawl(env: dict) -> Tuple[bool, str]:
    key = env.get("MCP_FIRECRAWL_API_KEY", "")
    if not key:
        return False, "нет ключа"
    code, text = _http("GET", "https://api.firecrawl.dev/v2/team/credit-usage",
                       {"Authorization": f"Bearer {key}"})
    if code != 200:
        return False, f"HTTP {code}"
    m = re.search(r'"remainingCredits":(\d+)', text)
    cr = f"{m.group(1)} кредитов" if m else "ключ валиден"
    tools = _mcp_tool_count("firecrawl")
    return True, (f"{tools} инструментов + {cr}" if tools else cr)


def _mcp_tool_count(server: str) -> Optional[int]:
    """Best-effort: last registered tool count for an MCP server from the log."""
    try:
        text = AGENT_LOG.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return None
    matches = re.findall(
        rf"MCP server '{re.escape(server)}' \(HTTP\): registered (\d+) tool", text)
    return int(matches[-1]) if matches else None


def _check_github(env: dict) -> Tuple[bool, str]:
    key = env.get("MCP_GITHUB_API_KEY", "")
    if not key:
        return False, "нет ключа"
    n = _mcp_tool_count("github")
    if n:
        return True, f"{n} инструментов"
    code, _ = _http("GET", "https://api.github.com/user",
                    {"Authorization": f"Bearer {key}",
                     "User-Agent": "hermes-selftest"})
    return code == 200, ("подключён" if code == 200 else f"HTTP {code}")


def _check_orchestration(cfg: dict) -> Tuple[bool, str]:
    """Verify SOUL.md routing map + delegation wiring are in place."""
    try:
        soul = SOUL_PATH.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return False, "нет SOUL.md"
    has_map = "routing map" in soul.lower() or "маршрутизац" in soul.lower()
    deleg = ((cfg.get("delegation") or {}).get("model") or "").strip()
    if has_map and deleg:
        return True, "карта в SOUL.md + делегирование задано"
    if has_map:
        return True, "карта в SOUL.md"
    return False, "карта не найдена"


# ---------------------------------------------------------------------- send

def _send_telegram(env: dict, text: str) -> None:
    token = env.get("TELEGRAM_BOT_TOKEN", "")
    chat = env.get("SELFTEST_CHAT_ID") or env.get("TELEGRAM_HOME_CHANNEL", "")
    if not token or not chat:
        print("[startup-selftest] no telegram token/chat; skipping send", flush=True)
        return
    payload = urllib.parse.urlencode({
        "chat_id": chat, "text": text, "disable_web_page_preview": "true",
    }).encode("utf-8")
    req = urllib.request.Request(
        f"https://api.telegram.org/bot{token}/sendMessage",
        data=payload, method="POST",
        headers={"Content-Type": "application/x-www-form-urlencoded"})
    try:
        with urllib.request.urlopen(req, timeout=HTTP_TIMEOUT) as resp:
            resp.read()
    except Exception as e:
        print(f"[startup-selftest] telegram send failed: {e}", flush=True)


def _run_selftest() -> None:
    env = _load_env()
    if env.get("SELFTEST_DISABLE") in ("1", "true", "True"):
        return
    cfg = _load_config()

    m = cfg.get("model") or {}
    main_provider, main_model = m.get("provider", ""), m.get("default", "")
    dele = cfg.get("delegation") or {}
    vis = ((cfg.get("auxiliary") or {}).get("vision") or {})
    fb = cfg.get("fallback_model") or {}

    checks = [
        ("Gateway", True, "OK"),
        (f"Основная модель ({main_model or '—'})",
         *_ping_model(env, main_provider, main_model)),
        (f"Делегирование ({dele.get('model') or '—'})",
         *_ping_model(env, dele.get("provider", ""), dele.get("model", ""))),
        (f"Vision ({vis.get('model') or '—'})",
         *_ping_model(env, vis.get("provider", ""), vis.get("model", ""))),
        (f"Fallback ({fb.get('model') or '—'})",
         *_ping_model(env, fb.get("provider", ""), fb.get("model", ""))),
        ("Perplexity (sonar)", *_ping_model(env, "perplexity", "sonar")),
        ("OpenRouter", *_check_openrouter(env)),
        ("GitHub MCP", *_check_github(env)),
        ("Firecrawl MCP", *_check_firecrawl(env)),
        ("Оркестрация (SOUL.md)", *_check_orchestration(cfg)),
    ]
    passed = sum(1 for _, ok, _ in checks if ok)
    total = len(checks)
    head = "✅" if passed == total else "⚠️"
    lines = [f"📊 Автотест Hermes ({passed}/{total} {head})", ""]
    for name, ok, detail in checks:
        lines.append(f"{'✅' if ok else '❌'} {name} — {detail}")
    lines.append("")
    lines.append("Тиры: основная → делегирование (sonnet-4.6) → MoA. "
                 "Маршрутизация — по карте в SOUL.md.")
    _send_telegram(env, "\n".join(lines))
    print(f"[startup-selftest] done: {passed}/{total} passed", flush=True)


async def handle(event_type: str, context: dict) -> None:
    # Run the blocking probes off the event loop so gateway startup is never
    # stalled by a slow network call.
    try:
        await asyncio.to_thread(_run_selftest)
    except Exception as e:
        print(f"[startup-selftest] error: {e}", flush=True)
