# Browser Agent

Autonomous AI agent that controls a web browser to complete complex tasks.
You describe the task in plain text — the agent figures out how to do it.

## Stack

- Python 3.11+, FastAPI, WebSocket
- Playwright (Chromium, headful)
- Anthropic API (claude-sonnet-4-5)
- Dual-channel perception: screenshot + accessibility tree

## Architecture

**ReAct loop:** Observe → Think → Act → Repeat

On each step the agent:
1. Calls `get_page_state()` — takes a screenshot and extracts interactive elements with coordinates
2. Analyzes both channels and decides what to do next
3. Executes an action (navigate, click, type, scroll, etc.)
4. Repeats until the task is complete

## Advanced Patterns

### 1. Dual-Channel Perception

On every step the agent calls `get_page_state()` which returns:

1. **Screenshot** (base64 JPEG) — passed as vision input to Claude
2. **Accessibility tree** — top 25 interactive elements with type, text, bbox

Claude uses both channels simultaneously:
- Vision for understanding layout, reading text, spotting buttons
- A11y tree for precise coordinates when clicking elements

This eliminates the need for hardcoded selectors entirely.
The agent discovers UI structure dynamically on every step.

### 2. Hierarchical Planning

Before executing a task the agent makes one lightweight API call
(no screenshot) and produces a plan of 3-5 high-level steps.
The plan is injected into the conversation context and guides execution.
The agent can deviate from the plan on its own when needed.

Pattern: **Plan → Execute → Adapt**

### 3. Context Management

- Full conversation history maintained across steps
- Screenshots rotated: only last 2 kept in context (older replaced with placeholder)
- Compression triggered at 200k chars to stay within token limits
- `max_tokens` capped at 1024 to reduce cost per step

## Setup

```bash
pip install -r requirements.txt
playwright install chromium
cp .env.example .env   # then add your ANTHROPIC_API_KEY
```

## Run

```bash
python main.py
# Open http://localhost:8000
```

The Playwright browser opens as a separate window — you can watch the agent work in real time.
The web UI (localhost:8000) shows only the agent's action log as a timeline.

## Usage

Type any browser task in the UI. Examples:

- "Go to hh.ru and find 3 AI engineer vacancies"
- "Open google.com and search for the weather in Amsterdam"
- "Read the last 10 emails in Gmail and identify spam"
- "Order a BBQ burger on Yandex.Eda from my usual place"

The agent will ask you (`ask_user`) if it needs credentials or clarification.
