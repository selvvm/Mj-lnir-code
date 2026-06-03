# Mjolnir

A terminal-based AI coding agent. Chat with it in your terminal and it reads,
writes, and edits your code, runs commands, searches the web, and keeps track of
multi-step work — calling tools and looping until your task is done.

It's built from scratch in Python and powered by an LLM over an OpenAI-compatible
API (DeepSeek by default; point it at any compatible endpoint to use another
provider).

```
✻ Mjolnir coding agent
› read requirements.txt and tell me which version of openai we depend on
  → read_file {"path": "requirements.txt"}
  ✓ read_file
We depend on openai 2.37.0.
```

## Features

- **Streaming chat** in a clean terminal UI, with input history.
- **Agentic tool loop** — the model calls tools, reads the results, and keeps going until it can answer.
- **File tools** — read, write, and exact-match edit files.
- **Search & shell** — regex code search and shell command execution.
- **Web access** — web search (no API key) and URL fetching with HTML-to-text.
- **Task list** — the agent plans and tracks multi-step work.
- **Persistent memory** — durable facts survive across runs and are surfaced back to the model.
- **Subagents** — delegate exploration or code review to isolated child agents.
- **Context pruning** — old messages are trimmed to stay within the context window.
- **Tool approval** — file-writing and shell commands ask before they run.
- **Sessions** — each conversation is isolated, with its own token and cost accounting.

## Tools

| Tool | What it does |
|---|---|
| `read_file` | Read a text file (size cap + binary guard) |
| `write_file` | Create or overwrite a file |
| `edit_file` | Exact string replacement with a uniqueness guard |
| `grep` | Regex search (ripgrep when available, else a Python fallback) |
| `run_shell` | Run a shell command in the working directory |
| `web_search` | Web search via DuckDuckGo (no API key) |
| `web_fetch` | Fetch a URL; HTML is converted to readable text |
| `todos` | A per-session task list |
| `memory` | Persistent key/value store across sessions |
| `code_explorer` | Read-only subagent that investigates the codebase |
| `code_reviewer` | Subagent that reviews code/diffs for issues |

Write and shell tools ask for confirmation before running.

## Getting started

Requires Python 3.10+ and an API key.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Add your key to a `.env` file in the project root:

```bash
DEEPSEEK_API_KEY=your-api-key-here
```

Then run:

```bash
python main.py
```

## Usage

Type a message and press **Enter**. Some things to try:

- *"Read requirements.txt and tell me the openai version"*
- *"List the Python files in tools/ and count them"*
- *"Use code_explorer to find how tools are registered"*
- *"Remember that I prefer 4-space indentation"*

Tool activity shows inline (`→ tool …` then `✓`/`✗`), and write/shell tools prompt
for approval. Use `↑`/`↓` for history and `exit` / `Ctrl+C` to quit.

## Configuration

Behavior is configured through `Config` in `config/config.py` — model, API
endpoint, context budget, approval mode, memory location, and pricing. To use a
different provider, point `base_url` and `model` at any OpenAI-compatible API.

## Security

This agent can read and modify files, run shell commands, and fetch from the
internet on your behalf. A few things to be aware of:

- **Shell and file-writing tools run real commands** against your machine.
  Write and shell tools ask for confirmation before running (disable with
  `auto_approve`), so review prompts before approving.
- **Subagents run autonomously.** A subagent (e.g. `code_reviewer`) can run its
  allowed tools, including shell, *without* a separate approval prompt — so be
  cautious running untrusted prompts.
- **Memory is stored in plaintext** at `~/.ai_coding_agent/memory.json`.
- Keep your API key in `.env` (gitignored) and never commit it.

Run it on code and in environments you trust.

## License

[MIT](LICENSE)
