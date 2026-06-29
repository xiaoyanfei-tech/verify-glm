---
name: verify-glm
description: Verify the active Claude Code endpoint really serves GLM-5.2 (vs misconfigured / spoofed / silently downgraded). Runs config inspection, API echo, ChatGLM tokenizer fingerprint, and the GLM-4.5+ reasoning_tokens field probe. Add --full to also probe the 1M context window (burns ~900K tokens of quota). Use when the user asks "am I really running GLM-5.2", suspects their endpoint was switched, or wants to confirm a self-hosted/proxied GLM deployment is real.
---

# verify-glm

A skill for verifying that the active Claude Code endpoint (`ANTHROPIC_BASE_URL` + `ANTHROPIC_MODEL`) really serves a GLM model — and specifically GLM-5.2 when configured for it.

## When to invoke

- User asks "am I really running GLM-5.2 / GLM-X" or any variant ("how do I know it's real", "verify the model")
- User suspects their proxy / gateway is silently substituting a different model
- User wants to confirm a freshly-set-up endpoint actually works end-to-end before relying on it
- Before relying on a 1M-context workflow, run with `--full` to confirm the window is actually 1M

## How to run

```bash
# Default 4 checks (fast, no quota cost beyond a few hundred tokens)
python ~/.claude/skills/verify-glm/verify_glm.py

# Plus 1M context window probe (sends ~900K tokens — may exhaust 5h quota)
python ~/.claude/skills/verify-glm/verify_glm.py --full

# Machine-readable
python ~/.claude/skills/verify-glm/verify_glm.py --json
```

On Windows where `python` may not be on PATH, use `py` or full path.

## What it checks

| # | Check | What it proves |
|---|-------|---------------|
| 1 | Config check | env / `~/.claude/settings.json` actually point at a GLM endpoint |
| 2 | API echo | The endpoint accepts the request and echoes the model name |
| 3 | Tokenizer fingerprint | The tokenizer is ChatGLM family (1 CN char ≈ 1 token, EN is subword — distinguishes from tiktoken / Qwen / Llama) |
| 4 | `reasoning_tokens` field | Response has the GLM-4.5+ specific usage field |
| 5 (opt) | Context window | ≥800K tokens accepted in a single request, consistent with 1M claim |

Default checks (1-4) confirm "this is a GLM-family model". Check 5 plus the configured model name being `glm-5.2` confirms 5.2 specifically (1M is the 5.2 differentiator vs 4.x at 200K).

## Interpreting output

- All ✅ → **trustworthy GLM endpoint**, no spoofing detected
- Echo ✅ but tokenizer ❌ → the gateway likely **substituted a non-GLM model** (e.g. Claude/GPT) while echoing the GLM name back
- Config ❌ → endpoint isn't set up at all; check `ANTHROPIC_BASE_URL` and `ANTHROPIC_MODEL`
- `reasoning_tokens` ❌ but everything else ✅ → likely a GLM-4 or earlier (not 4.5+); model card claim of 5.2 may be aspirational

## Files

- `verify_glm.py` — the actual checker (stdlib only, no deps)
- This file (`SKILL.md`) — invocation guide for future-me
