# Mjolnir

A terminal-based AI coding agent, built from scratch in Python on top of the
DeepSeek API. It streams replies into your terminal, calls tools to read and edit
your code, run commands, and search the web, and keeps a clean layered
architecture you can read end to end.

```
✻ Mjolnir coding agent
› read requirements.txt and tell me which version of openai we depend on
  → read_file {"path": "requirements.txt"}
  ✓ read_file
✻ DeepSeek
We depend on openai 2.37.0.
```

## Features

- **Streaming chat** in a bordered terminal UI (`click` + `rich` + `prompt_toolkit`), with input history.
- **Agentic tool loop** — the model calls tools, sees the results, and keeps going until it can answer.
- **11 built-in tools** — file read/write/edit, regex search, shell, web search/fetch, a task list, persistent memory, and two specialized subagents.
- **Sessions** — each conversation owns its own context, tools, working directory, and token/cost accounting.
- **Persistent memory** — durable facts survive across runs and are surfaced back into the system prompt.
- **Context pruning** — old messages are dropped to stay within the model's context window.
- **Tool approval** — file-writing and shell commands ask for confirmation before they run.
- **Subagents** — delegate exploration or code review to isolated child agents.

## Architecture

The codebase is split into thin layers, each speaking its own event type and
never leaking the layer below it.

```
 main.py            UI — terminal chat, streaming, tool/approval prompts
   │  AgentEvent
   ▼
 agent/agent.py     Agent — the agentic loop: stream → run tools → loop;
   │                          owns pruning + approval                        ┐
   │  StreamEvent                                                            │ operates on
   ▼                                                                         │
 client/llm_client.py   LLMClient — DeepSeek transport (OpenAI-compatible)   │
                                                                             ▼
 agent/session.py   Session — per-conversation STATE: config, client,
                              context, tool registry, cwd, token usage
   ├── context/manager.py   ContextManager — history, system prompt, pruning
   ├── config/config.py     Config — model, limits, pricing, paths
   ├── prompts/system.py    System prompt assembly (identity, env, memory…)
   └── tools/               Tool base class + registry + 11 tools
```

The key split: **`Agent` is behavior, `Session` is state.** The same `Agent` loop
can drive any `Session`, which is exactly what makes subagents trivial — a
subagent is just another `Agent` + `Session` pair.

## Tools

| Tool | Kind | What it does |
|---|---|---|
| `read_file` | read | Read a text file (size cap + binary guard) |
| `write_file` | write | Create/overwrite a file |
| `edit_file` | write | Exact string replacement with a uniqueness guard |
| `grep` | read | Regex search (ripgrep when available, else a Python fallback) |
| `run_shell` | shell | Run a shell command in the working directory |
| `web_search` | network | Web search via DuckDuckGo (no API key) |
| `web_fetch` | network | Fetch a URL; HTML is converted to readable text |
| `todos` | task | A per-session task list (add / complete / list / clear) |
| `memory` | memory | Persistent key/value store across sessions |
| `code_explorer` | agent | Read-only subagent that investigates the codebase |
| `code_reviewer` | agent | Subagent that reviews code/diffs for issues |

Each tool declares a `ToolKind`, which drives the approval policy (`write` and
`shell` require confirmation by default).

## Getting started

### Prerequisites

- Python 3.10+ (developed on 3.13)
- A DeepSeek API key — https://platform.deepseek.com
- Optional: [ripgrep](https://github.com/BurntSushi/ripgrep) for faster `grep` (a Python fallback is used otherwise)

### Install

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

This installs `openai`, `python-dotenv`, `click`, `rich`, and `prompt_toolkit`
(`pydantic` and `httpx` come bundled with `openai`).

### Configure your API key

Create a `.env` file in the project root:

```bash
DEEPSEEK_API_KEY=your-api-key-here
```

### Run

```bash
python main.py
```

## Usage

Type a message and press **Enter**. Try a tool-using prompt:

- *"Read requirements.txt and tell me the openai version"* → `read_file`
- *"List the Python files in tools/ and count them"* → `run_shell`
- *"Use code_explorer to find how tools are registered"* → a subagent investigates
- *"Remember that I prefer 4-space indentation"* → `memory`

Tool activity is shown inline (`→ tool …` then `✓`/`✗`), and write/shell tools
prompt for approval (`Allow? [y/N]`).

**Controls:** `↑`/`↓` input history · `exit` / `quit` / `Ctrl+C` / `Ctrl+D` to leave.

## Configuration

Everything is configured through `Config` (`config/config.py`):

| Field | Default | Purpose |
|---|---|---|
| `api_key` | `$DEEPSEEK_API_KEY` | DeepSeek API key |
| `base_url` | `https://api.deepseek.com` | API endpoint |
| `model` | `deepseek-chat` | Model name |
| `max_iterations` | `10` | Max LLM calls per turn (tool-loop cap) |
| `max_context_tokens` | `64000` | Context budget before pruning kicks in |
| `auto_approve` | `False` | Skip approval prompts for write/shell tools |
| `cwd` | current dir | Working directory tools resolve paths against |
| `memory_path` | `~/.ai_coding_agent/memory.json` | Where persistent memory is stored |
| `developer_instructions` / `user_instructions` | `None` | Extra system-prompt sections |
| `price_*_per_1m` | DeepSeek rates | Token pricing used for cost estimates |

## How it works

**The agentic loop** (`agent/agent.py`) — for each turn the Agent streams the
model's reply; if it contains tool calls, it runs them, feeds the results back,
and loops; if it's plain text, that's the final answer. A `max_iterations` cap
prevents runaway loops.

**Sessions** (`agent/session.py`) hold all per-conversation state and accumulate
token usage + an estimated cost. Two sessions are fully isolated.

**Memory** is a JSON-backed key/value store. At session start its keys are listed
in the system prompt, so the model knows what it remembers and can `memory get`
the values it needs.

**Context pruning** (`context/manager.py`) drops the oldest messages once the
context exceeds `max_context_tokens`, without ever orphaning a tool result.

**Approval** — before a `write`/`shell` tool runs, the Agent asks via a callback;
a denial is reported back to the model so it can adapt. `auto_approve` disables this.

**Subagents** (`tools/subagent.py`) spin up a fresh, isolated `Session` + `Agent`
with a restricted, read-only toolset, run a single task to completion, and return
only the final answer. They can't spawn further subagents (depth-1).

## Project structure

```
main.py                  Terminal UI and chat loop
agent/
  agent.py               The agentic loop, pruning, approval
  session.py             Per-conversation state container
  events.py              AgentEvent types the UI consumes
client/
  llm_client.py          DeepSeek transport (streaming + tool calls)
  response.py            StreamEvent / TokenUsage models
context/
  manager.py             Conversation history, system prompt, pruning
  text.py                Token-count heuristic
config/config.py         Config dataclass
prompts/system.py        System prompt assembly
tools/
  base.py                Tool base class, ToolKind, ToolResult
  registry.py            Tool registry
  read_file.py … subagent.py   The individual tools
```

## Roadmap

- Summarization-based context compaction (vs. the current drop-oldest pruning)
- Propagate tool approval into subagents
- Roll subagent token usage up into the parent session
- Parallel execution of independent tool calls

## License

No license file is included yet — add one before sharing publicly.
