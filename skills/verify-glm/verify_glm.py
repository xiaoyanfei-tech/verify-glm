#!/usr/bin/env python3
"""
verify-glm — Verify that the active Claude Code endpoint is really serving GLM-5.2.

Runs 4 default checks + 1 optional probe:
  1. Config check       — env vars / ~/.claude/settings.json point at a GLM endpoint
  2. API echo check     — POST /v1/chat/completions and verify response.model
  3. Tokenizer print    — Chinese char-level + English subword carbon proxy
  4. reasoning_tokens   — GLM-4.5+ specific response field
  5. (--full) context   — sends ~900K tokens to verify 1M context window

Reads config from (in priority order):
  - environment: ANTHROPIC_BASE_URL, ANTHROPIC_MODEL, ANTHROPIC_AUTH_TOKEN
  - ~/.claude/settings.json env section
  - ./.claude/settings.json env section (project-local)

Exit code 0 = all required checks pass. Non-zero = a check failed.

Usage:
  python verify_glm.py            # default 4 checks
  python verify_glm.py --full     # also run 1M context probe (burns quota)
  python verify_glm.py --json     # machine-readable JSON output
  python verify_glm.py --quiet    # only show summary line
"""
from __future__ import annotations
import argparse
import json
import os
import sys
import urllib.request
import urllib.error
from pathlib import Path
from typing import Any


# ---------- config loading ----------

def load_config() -> dict[str, str]:
    """Resolve base_url / model / token from env, then settings.json files."""
    cfg = {
        "base_url": os.environ.get("ANTHROPIC_BASE_URL", ""),
        "model": os.environ.get("ANTHROPIC_MODEL", ""),
        "token": os.environ.get("ANTHROPIC_AUTH_TOKEN")
                 or os.environ.get("ANTHROPIC_API_KEY", ""),
    }
    settings_paths = [
        Path.home() / ".claude" / "settings.json",
        Path.cwd() / ".claude" / "settings.json",
    ]
    for p in settings_paths:
        if not p.exists():
            continue
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            continue
        env = data.get("env", {})
        if not cfg["base_url"]:
            cfg["base_url"] = env.get("ANTHROPIC_BASE_URL", "")
        if not cfg["model"]:
            cfg["model"] = env.get("ANTHROPIC_MODEL", "")
        if not cfg["token"]:
            cfg["token"] = env.get("ANTHROPIC_AUTH_TOKEN") or env.get("ANTHROPIC_API_KEY", "")
    return cfg


def api_post(base_url: str, token: str, payload: dict, timeout: int = 60) -> dict:
    url = base_url.rstrip("/") + "/v1/chat/completions"
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read())


# ---------- checks ----------

def check_config(cfg: dict) -> tuple[bool, str, dict]:
    if not cfg["base_url"]:
        return False, "ANTHROPIC_BASE_URL not set in env or settings.json", {}
    if not cfg["model"]:
        return False, "ANTHROPIC_MODEL not set", {}
    if not cfg["token"]:
        return False, "ANTHROPIC_AUTH_TOKEN/API_KEY not set", {}
    model = cfg["model"].lower()
    glm_like = "glm" in model
    details = {
        "base_url": cfg["base_url"],
        "model": cfg["model"],
        "token_prefix": cfg["token"][:8] + "...",
    }
    if not glm_like:
        return False, f"Model '{cfg['model']}' does not look like a GLM model", details
    return True, "Configured for GLM", details


def check_api_echo(cfg: dict) -> tuple[bool, str, dict]:
    try:
        r = api_post(cfg["base_url"], cfg["token"], {
            "model": cfg["model"],
            "messages": [{"role": "user", "content": "PONG"}],
            "max_tokens": 5,
        })
    except urllib.error.HTTPError as e:
        return False, f"HTTP {e.code}: {e.read().decode()[:200]}", {}
    except Exception as e:
        return False, f"{type(e).__name__}: {e}", {}
    returned_model = r.get("model", "")
    details = {"requested": cfg["model"], "returned": returned_model}
    if not returned_model:
        return False, "Response has no 'model' field", details
    if returned_model.lower() != cfg["model"].lower():
        return False, f"Model mismatch: asked {cfg['model']}, got {returned_model}", details
    return True, f"API echoed model={returned_model}", details


def _count(cfg: dict, text: str) -> int | None:
    try:
        r = api_post(cfg["base_url"], cfg["token"], {
            "model": cfg["model"],
            "messages": [{"role": "user", "content": text}],
            "max_tokens": 1,
        })
        return r["usage"]["prompt_tokens"]
    except Exception:
        return None


def check_tokenizer(cfg: dict) -> tuple[bool, str, dict]:
    # baseline: chat-template overhead
    base = _count(cfg, "a")
    if base is None:
        return False, "Could not count baseline tokens", {}

    probes = [
        ("人工智能技术正在改变世界", 13, "cn_long"),   # 13 CN chars
        ("你好", 2, "cn_short"),                      # 2 CN chars
        ("Artificial intelligence", None, "en_phrase"),
    ]
    results = {}
    for text, chars, key in probes:
        total = _count(cfg, text)
        if total is None:
            return False, f"Failed to tokenize: {text[:20]}", results
        content = total - base
        results[key] = {"text": text, "total": total, "content": content}
        if chars is not None:
            results[key]["chars"] = chars
            results[key]["ratio"] = round(content / chars, 2)

    # Verdict logic
    cn_ratio_long = results["cn_long"]["ratio"]
    cn_ratio_short = results["cn_short"]["ratio"]
    en_tokens = results["en_phrase"]["content"]

    reasons = []
    # GLM/ChatGLM: 1 CN char ≈ 1 token (no word-level merges)
    if not (0.85 <= cn_ratio_long <= 1.20):
        reasons.append(f"CN long ratio {cn_ratio_long} not in [0.85, 1.20] — unexpected for ChatGLM tokenizer")
    if not (0.85 <= cn_ratio_short <= 1.20):
        reasons.append(f"CN short ratio {cn_ratio_short} not in [0.85, 1.20]")
    # 'Artificial intelligence' tokenizes to ~2 in tiktoken (GPT/Claude), 7+ in GLM
    if en_tokens < 4:
        reasons.append(f"'Artificial intelligence' = {en_tokens} tokens — looks like tiktoken cl100k, not GLM")

    if reasons:
        return False, " ; ".join(reasons), results
    return True, (
        f"CN char-level (ratio={cn_ratio_long}), "
        f"EN subword ({en_tokens} tokens) — matches ChatGLM family"
    ), results


def check_reasoning_field(cfg: dict) -> tuple[bool, str, dict]:
    """The completion_tokens_details.reasoning_tokens field is a GLM-4.5+ marker."""
    try:
        r = api_post(cfg["base_url"], cfg["token"], {
            "model": cfg["model"],
            "messages": [{"role": "user", "content": "Think briefly then say OK."}],
            "max_tokens": 64,
        })
    except Exception as e:
        return False, f"{type(e).__name__}: {e}", {}
    usage = r.get("usage", {})
    ctd = usage.get("completion_tokens_details", {})
    has_reasoning = "reasoning_tokens" in ctd
    has_cached = "cached_tokens" in usage.get("prompt_tokens_details", {})
    details = {
        "completion_tokens_details": ctd,
        "prompt_tokens_details": usage.get("prompt_tokens_details", {}),
    }
    if has_reasoning:
        return True, f"reasoning_tokens={ctd['reasoning_tokens']} (GLM-4.5+ feature)", details
    if has_cached:
        return True, "cached_tokens field present (Volcengine Ark feature)", details
    return False, "No reasoning_tokens or cached_tokens fields — not a GLM-4.5+ response shape", details


def check_context_window(cfg: dict) -> tuple[bool, str, dict]:
    """Send ~3.8 MB (~900K tokens) and verify it's accepted."""
    text = ("The quick brown fox jumps over the lazy dog. " * 80000)[:3800000]
    try:
        r = api_post(cfg["base_url"], cfg["token"], {
            "model": cfg["model"],
            "messages": [{"role": "user", "content": text + "\n\nReply: DONE"}],
            "max_tokens": 5,
        }, timeout=600)
    except urllib.error.HTTPError as e:
        body = e.read().decode()[:300]
        return False, f"HTTP {e.code}: {body}", {"sent_chars": len(text)}
    except Exception as e:
        return False, f"{type(e).__name__}: {e}", {"sent_chars": len(text)}
    n = r.get("usage", {}).get("prompt_tokens", 0)
    details = {"prompt_tokens": n, "sent_chars": len(text)}
    if n >= 800000:
        return True, f"Accepted {n:,} tokens (≥800K → consistent with 1M context)", details
    return False, f"Only {n:,} tokens accepted — below 1M-class window", details


# ---------- runner ----------

CHECKS = [
    ("config", "Config check", check_config),
    ("echo", "API echo", check_api_echo),
    ("tokenizer", "Tokenizer fingerprint", check_tokenizer),
    ("reasoning", "reasoning_tokens field", check_reasoning_field),
]


def run(full: bool, json_out: bool, quiet: bool) -> int:
    cfg = load_config()
    results = []
    all_pass = True

    for key, label, fn in CHECKS:
        ok, msg, details = fn(cfg)
        results.append({"key": key, "label": label, "pass": ok, "msg": msg, "details": details})
        if not ok:
            all_pass = False

    if full:
        ok, msg, details = check_context_window(cfg)
        results.append({"key": "context", "label": "1M context window", "pass": ok, "msg": msg, "details": details})
        if not ok:
            all_pass = False

    if json_out:
        print(json.dumps({"pass": all_pass, "model": cfg.get("model"), "checks": results}, ensure_ascii=False, indent=2))
        return 0 if all_pass else 1

    if not quiet:
        print(f"verify-glm — checking active endpoint")
        print(f"  base_url: {cfg.get('base_url') or '(unset)'}")
        print(f"  model:    {cfg.get('model') or '(unset)'}")
        print()
        for i, r in enumerate(results, 1):
            mark = "✅" if r["pass"] else "❌"
            print(f"[{i}/{len(results)}] {r['label']}")
            print(f"      {mark} {r['msg']}")
            if r["details"] and not r["pass"]:
                print(f"      details: {json.dumps(r['details'], ensure_ascii=False)[:200]}")
            print()

    passed = sum(1 for r in results if r["pass"])
    total = len(results)
    if all_pass:
        print(f"✅ Verified GLM family ({passed}/{total}). Model claims to be: {cfg.get('model')}")
        return 0
    print(f"❌ FAIL ({passed}/{total} passed). Model: {cfg.get('model')}")
    return 1


def main():
    p = argparse.ArgumentParser(description="Verify the active Claude Code endpoint is really serving GLM-5.2")
    p.add_argument("--full", action="store_true", help="Also run 1M context probe (burns ~900K tokens of quota)")
    p.add_argument("--json", action="store_true", help="Machine-readable JSON output")
    p.add_argument("--quiet", action="store_true", help="Only show the summary line")
    args = p.parse_args()
    sys.exit(run(args.full, args.json, args.quiet))


if __name__ == "__main__":
    main()
