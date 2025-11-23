You’re right—let’s make this **fully up-to-date and concrete**.

Below are **Python examples pinned to the latest SDK (0.1.6)** and the current CLI flags/behaviors, straight from Anthropic’s docs. I’ll also show the **headless CLI** bridge you can drive from Python for streaming + barge-in.

---

## Pin your deps (today)

```bash
# Python SDK (latest)
pip install "claude-agent-sdk==0.1.6"

# Claude Code CLI (required by the SDK runtime)
npm i -g @anthropic-ai/claude-code
# (CLI supports headless `-p`, streaming `--output-format stream-json`,
# model pinning, permission flags, etc.)
```

The PyPI page confirms **`claude-agent-sdk 0.1.6`** (released Oct 31, 2025) and notes **Claude Code 2.0.0+** is required. ([PyPI][1])
CLI flags like `--output-format json|stream-json`, `--include-partial-messages`, `--model`, `--allowedTools`, and session controls are documented here. ([docs.claude.com][2])

---

## 1) Minimal “one-shot” task (streaming) — `query()`

```python
# Python 3.10+
import anyio
from claude_agent_sdk import query, ClaudeAgentOptions, AssistantMessage, TextBlock

async def main() -> None:
    opts = ClaudeAgentOptions(
        cwd="/srv/repos/your-monorepo",       # VPS path
        model="claude-haiku-4-5-20251001",   # pin exact model or just "sonnet"
        allowed_tools=["Read", "Grep", "Glob", "Bash"],
        permission_mode="acceptEdits",        # 'plan' | 'ask' | 'acceptEdits' | 'auto'
        system_prompt=(
            "You are a senior engineer working on Flutter/Laravel. "
            "Prefer read/search; only run safe analyzers when needed."
        ),
        max_turns=3,                          # cap agentic loops
    )

    prompt = ("Locate where the CuttingElement widget renders its options list in Flutter, "
              "explain data flow briefly, then run 'dart analyze' only if necessary.")

    async for msg in query(prompt=prompt, options=opts):
        if isinstance(msg, AssistantMessage):
            for block in msg.content:
                if isinstance(block, TextBlock):
                    print(block.text)

anyio.run(main)
```

`query()` is an async iterator that streams structured messages (good fit for piping into TTS). This interface and option names are shown on the SDK’s PyPI page for **0.1.6**. ([PyPI][1])
For exact model pinning, the CLI docs demonstrate `--model claude-sonnet-4-5-20250929`; the SDK accepts the same string. ([docs.claude.com][2])

---

## 2) Long-lived session + **streaming** + **barge-in/interrupt**

```python
import anyio
from claude_agent_sdk import ClaudeSDKClient, ClaudeAgentOptions, AssistantMessage, TextBlock

async def voice_session():
    opts = ClaudeAgentOptions(
        cwd="/srv/repos/your-monorepo",
        model="claude-haiku-4-5-20251001",
        allowed_tools=["Read", "Grep", "Glob", "Bash"],
        permission_mode="acceptEdits",
    )

    async with ClaudeSDKClient(options=opts) as client:
        # Turn 1
        await client.query("Scan for deprecated Radio API usage in Flutter and suggest a safe refactor.")
        async for msg in client.receive_response():         # stream text for TTS
            if isinstance(msg, AssistantMessage):
                for b in msg.content:
                    if isinstance(b, TextBlock):
                        print("SAY:", b.text)

        # User barges in: interrupt current run and pivot
        await client.query("Stop. Instead, grep 'RadioListTile' usage counts.")
        await client.interrupt()  # hook this to your VAD/ASR barge-in signal

        # Follow-up
        await client.query("Summarize the grep results only (bullet points).")
        async for msg in client.receive_response():
            print(msg)

anyio.run(voice_session)
```

`ClaudeSDKClient` is the persistent, bidirectional client; the SDK docs describe message streaming and interrupts in this class. ([PyPI][1])

---

## 3) Guardrails with **hooks** (deny risky bash before it runs)

```python
import anyio
from claude_agent_sdk import ClaudeAgentOptions, ClaudeSDKClient, HookMatcher

async def main():
    async def block_bad_bash(input_data, tool_use_id, context):
        # Only scrutinize Bash tool uses
        if input_data.get("tool_name") != "Bash":
            return {}
        cmd = input_data.get("tool_input", {}).get("command", "")
        if "rm -rf" in cmd or "docker" in cmd:
            # Deny with an explanation shown to Claude
            return {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "deny",
                    "permissionDecisionReason": "Dangerous command blocked by policy."
                }
            }
        return {}

    opts = ClaudeAgentOptions(
        cwd="/srv/repos/your-monorepo",
        allowed_tools=["Bash", "Read", "Grep"],
        hooks={"PreToolUse": [HookMatcher(matcher="Bash", hooks=[block_bad_bash])]},
    )

    async with ClaudeSDKClient(options=opts) as client:
        await client.query("Try to run: docker pull ubuntu && rm -rf /tmp/example")
        async for msg in client.receive_response():
            print(msg)

anyio.run(main)
```

Hook names and the `HookMatcher` pattern appear in the package reference with a full hooks example. ([PyPI][1])

---

## 4) Expose **your** remote executor as an SDK MCP tool (call your VPS microservice)

```python
import anyio, json
from typing import Any
from claude_agent_sdk import tool, create_sdk_mcp_server, ClaudeAgentOptions, ClaudeSDKClient
import httpx

@tool("safe_exec", "Run an allowlisted command via cloud-code daemon", {"cmd": str})
async def safe_exec(args: dict[str, Any]) -> dict[str, Any]:
    cmd = args["cmd"]
    if cmd not in {"dart analyze", "php artisan test", "composer validate"}:
        return {"content": [{"type": "text", "text": "Command not allowed."}]}

    # Call your remote, sandboxed executor (timeout + logs redaction recommended)
    async with httpx.AsyncClient(timeout=30.0) as client:
        r = await client.post("https://your-vps.example/exec", json={"cmd": cmd})
        data = r.json()
    return {"content": [{"type": "text", "text": f"Result:\n{json.dumps(data, indent=2)}"}]}

server = create_sdk_mcp_server(name="cloudcode", version="1.0.0", tools=[safe_exec])

opts = ClaudeAgentOptions(
    cwd="/srv/repos/your-monorepo",
    mcp_servers={"cloudcode": server},
    allowed_tools=["mcp__cloudcode__safe_exec", "Read", "Grep"]
)

async def main():
    async with ClaudeSDKClient(options=opts) as client:
        await client.query("Run dart analyze and summarize only the top 5 issues.")
        async for msg in client.receive_response():
            print(msg)

anyio.run(main)
```

The **in-process SDK MCP server** pattern (`@tool`, `create_sdk_mcp_server`, `allowed_tools` with `mcp__server__tool` naming) is documented in the SDK reference page. ([PyPI][1])
For external MCP servers (HTTP/stdio) and add commands like `claude mcp add …`, see the MCP guide. ([docs.claude.com][3])

---

## 5) Prefer the **headless CLI** when you want raw JSONL streaming from Python

```python
import asyncio, json, shlex

async def run_claude_headless(prompt: str):
    cmd = (
        'claude -p '                       # non-interactive
        '--output-format stream-json '     # JSONL stream
        '--include-partial-messages '      # stream partials for ultra-low latency
        '--allowedTools "Read,Grep,Glob,Bash" '
        '--permission-mode acceptEdits '
        f'{shlex.quote(prompt)}'
    )
    proc = await asyncio.create_subprocess_shell(
        cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
    )
    assert proc.stdout
    async for raw in proc.stdout:
        try:
            event = json.loads(raw.decode().strip())
        except json.JSONDecodeError:
            continue
        yield event  # each line: init | user | assistant | result

    await proc.wait()

# Example: pipe assistant text blocks to your TTS
async def main():
    async for ev in run_claude_headless("Explain build failures and propose concrete fixes."):
        if ev.get("type") == "assistant":
            for block in ev.get("message", {}).get("content", []):
                if block.get("type") == "text":
                    print("TTS:", block["text"])

asyncio.run(main())
```

Headless **`-p`** mode plus **`--output-format json|stream-json`**, partials, and session controls (`--resume`, `--continue`) are documented here; the page also shows the JSON schema including `session_id`, `num_turns`, and `duration_ms`. ([docs.claude.com][4])
Full CLI flag table (including **`--model`** and granular permission flags) is here. ([docs.claude.com][2])

---

## 6) Session persistence from Python (resume a multi-turn headless session)

```python
import asyncio, json, subprocess, shlex

def start_session(prompt: str) -> str:
    out = subprocess.check_output(
        f'claude -p {shlex.quote(prompt)} --output-format json', shell=True
    ).decode()
    return json.loads(out)["session_id"]

def continue_session(session_id: str, prompt: str) -> None:
    subprocess.run(
        f'claude -p --resume {shlex.quote(session_id)} {shlex.quote(prompt)} '
        '--output-format stream-json', shell=True, check=True
    )

sid = start_session("Start a debugging session for the checkout flow.")
continue_session(sid, "Run `php artisan test` and summarize failures.")
```

The headless docs show `--resume <session-id>` and `--continue` usage for multi-turn. ([docs.claude.com][4])

---

## 7) Sandboxing on your VPS (recommended)

* Enable the **sandboxed Bash** tool (`/sandbox` or corresponding settings).
* It enforces **filesystem** and **network** boundaries (Linux uses **bubblewrap**; macOS uses **Seatbelt**). You can allowlist directories/hosts and route egress through a proxy. ([docs.claude.com][5])
* Keep “escape hatch” disabled for production (`allowUnsandboxedCommands: false`) unless you explicitly need it. ([docs.claude.com][5])

---

### Notes (why this matches “latest”)

* **SDK**: `claude-agent-sdk==0.1.6` is the current PyPI latest and includes the APIs above (`query`, `ClaudeSDKClient`, hooks, in-process MCP tools). ([PyPI][1])
* **CLI**: the docs list **current flags** and demonstrate **model pinning** with `claude-sonnet-4-5-20250929`, plus `stream-json` and partials for low-latency streams. ([docs.claude.com][2])
* **MCP**: official guide shows how to connect HTTP/stdio servers and the recommended transports as of 2025. ([docs.claude.com][3])

If you share your VPS repo paths + which commands you’ll allow (e.g., `dart analyze`, `php artisan test`), I’ll tailor the `allowed_tools`, hooks, and the MCP tool skeleton exactly to your setup.

[1]: https://pypi.org/project/claude-agent-sdk/ "claude-agent-sdk · PyPI"
[2]: https://docs.claude.com/en/docs/claude-code/cli-reference "CLI reference - Claude Docs"
[3]: https://docs.claude.com/en/docs/claude-code/mcp "Connect Claude Code to tools via MCP - Claude Docs"
[4]: https://docs.claude.com/en/docs/claude-code/headless "Headless mode - Claude Docs"
[5]: https://docs.claude.com/en/docs/claude-code/sandboxing "Sandboxing - Claude Docs"
