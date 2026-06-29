# verify-glm

> One-shot verifier: is your Claude Code endpoint really serving **GLM-5.2**?

A Claude Code skill + standalone Python script that probes the active endpoint (`ANTHROPIC_BASE_URL` + `ANTHROPIC_MODEL`) and tells you in 30 seconds whether you're really getting GLM — not a silently-substituted Claude / GPT / Qwen pretending to be GLM, not a misconfigured proxy.

[English](#english) | [中文](#中文)

---

## English

### Why this exists

If you point Claude Code at a third-party gateway (Volcengine Ark, OpenRouter, your own proxy, ...) and configure `ANTHROPIC_MODEL=glm-5.2`, the gateway *might* be lying:

- It can echo `"model": "glm-5.2"` in the response while routing to a cheaper model
- It can show `glm-5.2` in `/v1/models` while serving GLM-4 behind it
- The model itself will, when asked, cheerfully claim to be whatever its system prompt says

You need **out-of-band evidence**. This tool gives you four:

| # | Check | Why it's hard to fake |
|---|-------|----------------------|
| 1 | Config inspection | Verifies the local config actually says GLM (catches typos / mis-set env) |
| 2 | API echo | Confirms the endpoint accepts requests and replies with the expected model name |
| 3 | **Tokenizer fingerprint** | Counts tokens for fixed strings — different tokenizers give different counts. ChatGLM gives `1 CN char ≈ 1 token` and `"Artificial intelligence" → 7 tokens`. tiktoken (Claude/GPT) and Qwen produce different patterns. **The gateway cannot rewrite token counts** without breaking billing. |
| 4 | `reasoning_tokens` field | GLM-4.5+ exposes `completion_tokens_details.reasoning_tokens` in usage. Claude/GPT use different shapes. |
| 5 (opt) | 1M context probe | Sends ~900K tokens. Only GLM-5.2 (and a few other frontier models) accept this. GLM-4 caps at 200K. |

Pass checks 1-4 → it's a GLM-family endpoint. Pass 5 → it's specifically the 1M-context generation (GLM-5.2).

### Install

```bash
# Clone
git clone https://github.com/<you>/verify-glm.git
cd verify-glm

# Linux / macOS / Git Bash
./install.sh

# Windows PowerShell
.\install.ps1
```

Or just copy `skills/verify-glm/` into `~/.claude/skills/` manually.

### Use

From within Claude Code: just ask *"verify I'm running GLM-5.2"* — Claude will discover the `verify-glm` skill and run it.

Or directly:

```bash
# Default 4 checks (fast, ~hundreds of tokens)
python ~/.claude/skills/verify-glm/verify_glm.py

# Plus 1M context probe (sends ~900K tokens — burns 5h quota on most plans)
python ~/.claude/skills/verify-glm/verify_glm.py --full

# Machine-readable
python ~/.claude/skills/verify-glm/verify_glm.py --json
```

### Sample output

```
verify-glm — checking active endpoint
  base_url: https://<your-glm-gateway>/v1
  model:    glm-5.2

[1/4] Config check
      ✅ Configured for GLM

[2/4] API echo
      ✅ API echoed model=glm-5.2

[3/4] Tokenizer fingerprint
      ✅ CN char-level (ratio=0.92), EN subword (7 tokens) — matches ChatGLM family

[4/4] reasoning_tokens field
      ✅ reasoning_tokens=0 (GLM-4.5+ feature)

✅ Verified GLM family (4/4). Model claims to be: glm-5.2
```

### Interpreting failures

| Failure | What it likely means |
|---------|---------------------|
| Config ❌ | `ANTHROPIC_BASE_URL` or `ANTHROPIC_MODEL` not set; check env and `~/.claude/settings.json` |
| Echo ❌ HTTP 401/403 | Token wrong / expired |
| Echo ❌ HTTP 400 | Model name not recognized by the gateway |
| Tokenizer ❌ "looks like tiktoken cl100k" | Gateway is **silently substituting Claude or GPT-4** while echoing the GLM name |
| Tokenizer ❌ CN ratio < 0.85 | Different tokenizer (Qwen / Llama / custom) — not GLM family |
| `reasoning_tokens` ❌ | Probably a pre-4.5 GLM, or a non-GLM model |
| `--full` ❌ HTTP 400 InvalidParameter | Context window < 800K — not GLM-5.2 (probably GLM-4 at 200K) |

### Config resolution order

The script reads from (first match wins):

1. Environment variables: `ANTHROPIC_BASE_URL`, `ANTHROPIC_MODEL`, `ANTHROPIC_AUTH_TOKEN` (or `ANTHROPIC_API_KEY`)
2. `~/.claude/settings.json` → `env` section
3. `./.claude/settings.json` → `env` section (project-local override)

### Limitations

- The tokenizer fingerprint identifies the **family** (ChatGLM-style vs tiktoken vs Qwen). It can't strictly distinguish GLM-4 from GLM-5.2 — that's what the `--full` context probe is for.
- A really determined adversarial gateway could record-and-replay tokenizations from a real GLM endpoint. None of the public gateways are known to do this.
- Network errors / quota-exceeded errors are reported as failures even though they don't mean the model is fake. Re-run when network is healthy.

### Dependencies

None. Pure Python 3.8+ stdlib (`urllib`, `json`, `argparse`).

### License

MIT — see [LICENSE](LICENSE).

---

## 中文

### 这玩意儿干嘛的

你把 Claude Code 接到第三方网关（火山方舟、OpenRouter、自建代理...）并设 `ANTHROPIC_MODEL=glm-5.2` 时，网关**有可能在骗你**：

- 响应里 `"model": "glm-5.2"` 可以随便填，实际后端跑的可能是更便宜的模型
- `/v1/models` 列表可以包含 `glm-5.2`，背后实际服务 GLM-4
- 直接问模型"你是谁"也不算证据——它会按 system prompt 说什么是什么

你需要**带外证据**。本工具提供 4 条：

| # | 检查项 | 为什么难伪造 |
|---|--------|-------------|
| 1 | 配置检查 | 本机配置确实写的是 GLM（防 typo / 环境变量没生效） |
| 2 | API 回显 | 接口能调通，返回的 model 字段匹配 |
| 3 | **Tokenizer 指纹** | 固定字符串的 token 数是模型的指纹。ChatGLM：`1 中文字 ≈ 1 token`、`"Artificial intelligence" → 7 token`。tiktoken（Claude/GPT）、Qwen 的数完全不同。**网关没法改 token 数**——计费要靠它。 |
| 4 | `reasoning_tokens` 字段 | GLM-4.5+ 在 usage 里返回 `completion_tokens_details.reasoning_tokens`。Claude/GPT 字段结构不一样。 |
| 5（可选） | 1M 上下文探测 | 发 ~900K token。只有 GLM-5.2 这种前沿模型吃得下。GLM-4 上限 200K。 |

1-4 全过 → 是 GLM 家族。再过 5 → 是 1M 上下文这一代（GLM-5.2）。

### 安装

```bash
git clone https://github.com/<你>/verify-glm.git
cd verify-glm

# Linux / macOS / Git Bash
./install.sh

# Windows PowerShell
.\install.ps1
```

或者直接把 `skills/verify-glm/` 拷到 `~/.claude/skills/`。

### 使用

**在 Claude Code 里**：直接说"验证一下我是不是真的在跑 GLM-5.2"——Claude 会自动发现并调用这个 skill。

**直接命令行**：

```bash
# 默认 4 项检查（快，几百 token）
python ~/.claude/skills/verify-glm/verify_glm.py

# 加 1M 上下文探测（会发 ~900K token，可能耗光 5 小时配额）
python ~/.claude/skills/verify-glm/verify_glm.py --full

# JSON 输出
python ~/.claude/skills/verify-glm/verify_glm.py --json
```

### 失败诊断

| 失败 | 原因 |
|------|------|
| 配置 ❌ | `ANTHROPIC_BASE_URL` / `ANTHROPIC_MODEL` 没设 |
| 回显 ❌ HTTP 401/403 | Token 错或过期 |
| 回显 ❌ HTTP 400 | 网关不认这个模型名 |
| Tokenizer ❌ "looks like tiktoken cl100k" | 网关**偷偷换成了 Claude 或 GPT-4**，model 字段是假的 |
| Tokenizer ❌ CN ratio < 0.85 | 是别的 tokenizer（Qwen / Llama / 自研），不是 GLM 家族 |
| `reasoning_tokens` ❌ | 大概是 4.5 之前的 GLM，或者根本不是 GLM |
| `--full` ❌ HTTP 400 InvalidParameter | 上下文窗口 < 800K，不是 GLM-5.2（可能是 GLM-4 200K） |

### 配置读取顺序

按下面顺序，先命中先用：

1. 环境变量 `ANTHROPIC_BASE_URL`、`ANTHROPIC_MODEL`、`ANTHROPIC_AUTH_TOKEN`（或 `ANTHROPIC_API_KEY`）
2. `~/.claude/settings.json` 的 `env` 段
3. `./.claude/settings.json` 的 `env` 段（项目级覆盖）

### 局限

- Tokenizer 指纹能识别**家族**（ChatGLM-style / tiktoken / Qwen），但严格区分 GLM-4 和 GLM-5.2 需要 `--full` 跑上下文探测。
- 极端对抗场景下，网关可以预先从真 GLM 端点录制 tokenization 结果再重放——目前公开网关没人这么干。
- 网络抖动、配额耗尽都会报失败，并不代表模型是假的，恢复网络后重跑即可。

### 依赖

零依赖。Python 3.8+ 标准库（`urllib` / `json` / `argparse`）就够。

### License

MIT — 见 [LICENSE](LICENSE)。
