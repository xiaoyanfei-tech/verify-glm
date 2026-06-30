# verify-glm

[![Python](https://img.shields.io/badge/python-3.8%2B-blue)](#dependencies)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![Claude Code Skill](https://img.shields.io/badge/Claude%20Code-skill-purple)](#use-with-claude-code)
[![Model Verification](https://img.shields.io/badge/model-verification-orange)](#what-it-checks)

> Verify whether your Claude Code endpoint is really serving **GLM-5.2** — using tokenizer fingerprinting, reasoning-token checks, config inspection, and an optional 1M context probe.
>
> **verify-glm is not another LLM eval framework. It verifies whether the model behind your Claude Code / LLM gateway is actually the model you think it is.**
>
> **verify-glm 不是又一个模型评测框架，它验证的是：你接入的 Claude Code / LLM 网关背后，到底是不是真的那个模型。**

`verify-glm` is a Claude Code skill + standalone Python CLI for developers who route Claude Code through a GLM-compatible / OpenAI-compatible gateway and want evidence that the backend model is actually GLM-5.2, not a silently substituted or downgraded model.

[English](#english) | [中文](#中文)

---

## English

### Why verify?

If you configure Claude Code with `ANTHROPIC_MODEL=glm-5.2`, you still might not be talking to GLM-5.2.

A gateway can:

- echo `"model": "glm-5.2"` while routing to a cheaper model
- list `glm-5.2` in `/v1/models` while serving GLM-4 or another backend
- hide routing changes behind an OpenAI-compatible or Claude-compatible API
- pass a simple "who are you?" prompt because the model follows the system prompt

You need **out-of-band evidence**. `verify-glm` gives you that evidence in a reproducible CLI report.

### Who is this for?

- Claude Code users routing through a GLM-5.2 endpoint
- Developers using OpenAI-compatible or Claude-compatible LLM gateways
- Teams evaluating GLM-5.2 for AI coding workflows
- Engineers who need to verify tokenizer behavior, reasoning-token metadata, or long-context support
- Anyone asking: "Is this endpoint really GLM-5.2?"

### What it checks

| # | Check | Why it matters |
|---|-------|----------------|
| 1 | Config inspection | Verifies local Claude Code config / env actually points at GLM |
| 2 | API echo | Confirms the endpoint accepts requests and returns the expected model name |
| 3 | **Tokenizer fingerprint** | Fixed strings produce model-family-specific token counts. ChatGLM-style tokenization is visibly different from tiktoken / Qwen / Llama families. |
| 4 | `reasoning_tokens` field | GLM-4.5+ exposes `completion_tokens_details.reasoning_tokens` in usage metadata. |
| 5 optional | 1M context probe | Sends a near-1M-token prompt to test whether long-context support is real. |

Passing checks 1-4 means the endpoint is likely GLM-family. Passing the optional long-context probe gives stronger evidence for GLM-5.2-class context support.

### Example result

```text
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

With `--full`, the tool also runs the long-context probe:

```text
[5/5] 1M context probe
      ✅ accepted ~900K tokens

Verdict: likely GLM-5.2-class endpoint
```

### Use with Claude Code

After installation, ask Claude Code:

```text
verify I'm running GLM-5.2
```

Claude Code will discover the `verify-glm` skill and run the verifier.

### Install

```bash
git clone https://github.com/xiaoyanfei-tech/verify-glm.git
cd verify-glm

# Linux / macOS / Git Bash
./install.sh

# Windows PowerShell
.\install.ps1
```

Or copy `skills/verify-glm/` into `~/.claude/skills/` manually.

### CLI usage

```bash
# Default 4 checks: fast, low token usage
python ~/.claude/skills/verify-glm/verify_glm.py

# Add 1M context probe: expensive, use only when needed
python ~/.claude/skills/verify-glm/verify_glm.py --full

# Machine-readable output
python ~/.claude/skills/verify-glm/verify_glm.py --json
```

### Shareable badge

If this tool helps you verify your setup, you can add a badge to your project README:

```md
[![Verified by verify-glm](https://img.shields.io/badge/verified%20by-verify--glm-blue)](https://github.com/xiaoyanfei-tech/verify-glm)
```

Rendered badge:

[![Verified by verify-glm](https://img.shields.io/badge/verified%20by-verify--glm-blue)](https://github.com/xiaoyanfei-tech/verify-glm)

### Interpreting failures

| Failure | What it likely means |
|---------|---------------------|
| Config ❌ | `ANTHROPIC_BASE_URL` or `ANTHROPIC_MODEL` is missing / misconfigured |
| Echo ❌ HTTP 401/403 | API token is wrong, expired, or blocked |
| Echo ❌ HTTP 400 | Model name not recognized by the gateway |
| Tokenizer ❌ looks like tiktoken | Gateway may be routing to Claude / GPT-style backend while echoing GLM |
| Tokenizer ❌ CN ratio too low | Tokenizer likely belongs to another model family such as Qwen / Llama / custom |
| `reasoning_tokens` ❌ | Could be pre-4.5 GLM, non-GLM, or gateway stripping usage details |
| `--full` ❌ context error | Context window is likely below GLM-5.2-class long-context capacity |

### Config resolution order

The script reads credentials and endpoint config from:

1. Environment variables: `ANTHROPIC_BASE_URL`, `ANTHROPIC_MODEL`, `ANTHROPIC_AUTH_TOKEN` or `ANTHROPIC_API_KEY`
2. `~/.claude/settings.json` → `env`
3. `./.claude/settings.json` → `env`

### Need help?

If you're setting up Claude Code with GLM-5.2 in a corporate, proxy-heavy, or custom-gateway environment, this tool can help diagnose common routing and model-verification issues.

For setup help, endpoint verification reports, or enterprise AI coding environment consulting, open a GitHub issue with your use case.

### Limitations

- This is evidence-based verification, not a cryptographic proof of model identity.
- Tokenizer fingerprinting identifies the model family; the optional long-context probe gives stronger GLM-5.2-class evidence.
- Network errors, quota limits, and gateway filtering can look like verification failures. Re-run when the environment is healthy.
- A determined adversarial gateway could theoretically proxy selected checks to a real GLM endpoint.

### Dependencies

None. Pure Python 3.8+ standard library.

### License

MIT — see [LICENSE](LICENSE).

---

## 中文

### 这个项目是什么？

`verify-glm` 是一个 Claude Code skill + Python 命令行工具，用来验证你当前接入的 Claude Code endpoint 是否真的在跑 **GLM-5.2**。

它不是简单问模型"你是谁"，而是用：

- 配置检查
- API 回显
- Tokenizer 指纹
- `reasoning_tokens` 元数据
- 可选 1M 上下文探测

来判断后端是否像真正的 GLM-5.2。

### 为什么需要验证？

你把 Claude Code 配成 `ANTHROPIC_MODEL=glm-5.2`，不代表后端一定是真的 GLM-5.2。

网关可能：

- 响应里写 `"model": "glm-5.2"`，实际后端跑更便宜的模型
- `/v1/models` 列表里有 `glm-5.2`，实际路由到 GLM-4 或别的模型
- 在 OpenAI-compatible / Claude-compatible API 后面悄悄换模型
- 让模型按 system prompt 自称 GLM，骗过普通问答

所以你需要**带外证据**。`verify-glm` 就是用可复现的检测项给你证据。

### 适合谁？

- 正在用 Claude Code 接 GLM-5.2 的开发者
- 使用 OpenAI-compatible / Claude-compatible 网关的人
- 正在评估 GLM-5.2 做 AI Coding 的团队
- 想确认上下文窗口、tokenizer、reasoning metadata 是否真实的人
- 担心模型被替换、降级、代理转发的人

### 检查什么？

| # | 检查项 | 作用 |
|---|--------|------|
| 1 | 配置检查 | 确认本机 Claude Code 配置确实指向 GLM |
| 2 | API 回显 | 确认 endpoint 可用，并返回期望 model 名 |
| 3 | **Tokenizer 指纹** | 固定字符串 token 数能反映模型家族；ChatGLM-style 与 tiktoken / Qwen / Llama 差异明显 |
| 4 | `reasoning_tokens` 字段 | GLM-4.5+ 会在 usage metadata 里返回该字段 |
| 5 可选 | 1M 上下文探测 | 发送接近 1M token 的 prompt，验证长上下文是否真实 |

1-4 全过，说明大概率是 GLM 家族。再跑过 `--full`，则更接近 GLM-5.2 级别长上下文能力。

### 示例输出

```text
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

加 `--full` 后会额外跑 1M 上下文探测：

```text
[5/5] 1M context probe
      ✅ accepted ~900K tokens

Verdict: likely GLM-5.2-class endpoint
```

### 在 Claude Code 里使用

安装后，直接对 Claude Code 说：

```text
验证一下我是不是真的在跑 GLM-5.2
```

Claude Code 会发现 `verify-glm` skill 并运行检测。

### 安装

```bash
git clone https://github.com/xiaoyanfei-tech/verify-glm.git
cd verify-glm

# Linux / macOS / Git Bash
./install.sh

# Windows PowerShell
.\install.ps1
```

也可以直接把 `skills/verify-glm/` 拷贝到 `~/.claude/skills/`。

### 命令行使用

```bash
# 默认 4 项检查：快，token 消耗低
python ~/.claude/skills/verify-glm/verify_glm.py

# 加 1M 上下文探测：消耗大，只在需要时跑
python ~/.claude/skills/verify-glm/verify_glm.py --full

# JSON 输出
python ~/.claude/skills/verify-glm/verify_glm.py --json
```

### 可分享 badge

如果这个工具帮你验证了环境，可以把 badge 放到你的 README：

```md
[![Verified by verify-glm](https://img.shields.io/badge/verified%20by-verify--glm-blue)](https://github.com/xiaoyanfei-tech/verify-glm)
```

效果：

[![Verified by verify-glm](https://img.shields.io/badge/verified%20by-verify--glm-blue)](https://github.com/xiaoyanfei-tech/verify-glm)

### 失败怎么理解？

| 失败 | 可能原因 |
|------|----------|
| 配置 ❌ | `ANTHROPIC_BASE_URL` / `ANTHROPIC_MODEL` 没设置或设置错 |
| 回显 ❌ HTTP 401/403 | API token 错误、过期或被拦截 |
| 回显 ❌ HTTP 400 | 网关不认识这个模型名 |
| Tokenizer ❌ 像 tiktoken | 可能被路由到 Claude / GPT 风格后端，但 model 字段仍写 GLM |
| Tokenizer ❌ 中文 ratio 太低 | 可能是 Qwen / Llama / 自研 tokenizer，不是 GLM 家族 |
| `reasoning_tokens` ❌ | 可能是 4.5 之前的 GLM，也可能不是 GLM，或网关删掉了 usage 细节 |
| `--full` ❌ 上下文错误 | 上下文窗口很可能低于 GLM-5.2 级别 |

### 配置读取顺序

脚本按以下顺序读取配置：

1. 环境变量：`ANTHROPIC_BASE_URL`、`ANTHROPIC_MODEL`、`ANTHROPIC_AUTH_TOKEN` 或 `ANTHROPIC_API_KEY`
2. `~/.claude/settings.json` 的 `env`
3. `./.claude/settings.json` 的 `env`

### 需要帮助？

如果你正在企业网络、代理环境、自建网关里配置 Claude Code + GLM-5.2，这个工具可以帮助诊断常见的模型路由和配置问题。

如需 endpoint 验证报告、Claude Code 接入配置、企业 AI Coding 环境排障，可以开 GitHub issue 描述你的场景。

### 局限

- 这是基于证据的验证，不是密码学级别的模型身份证明。
- Tokenizer 指纹主要识别模型家族；`--full` 长上下文探测能提供更强的 GLM-5.2 级别证据。
- 网络错误、配额耗尽、网关过滤都可能表现为验证失败，环境恢复后需要重跑。
- 极端对抗场景下，恶意网关理论上可以把部分检测转发给真实 GLM endpoint。

### 依赖

零依赖。Python 3.8+ 标准库即可。

### License

MIT — 见 [LICENSE](LICENSE)。
