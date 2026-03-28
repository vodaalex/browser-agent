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

### 3. Tool Consolidation

По рекомендации Anthropic — консолидация overlapping tools.
Убран дублирующий tool `screenshot` (заменён `get_page_state`).
Добавлен `type_and_submit` — объединяет click+type+Enter в один вызов.
Сокращает количество шагов для поиска с 3 до 1.

### 4. Context Management

- Full conversation history maintained across steps
- Screenshots rotated: only last 2 kept in context (older replaced with placeholder)
- Compression triggered at 200k chars to stay within token limits
- `max_tokens` capped at 1024 to reduce cost per step

## Technical Decisions

### Почему Playwright
Async-first API совместим с asyncio архитектурой.
Встроенный accessibility tree через query_selector_all.
Надёжная обработка динамических страниц через networkidle.
Лучше Selenium по скорости, лучше Puppeteer по Python-поддержке.

### Почему Anthropic API напрямую
Прямой контроль над форматом сообщений — критично для multimodal
(скриншоты передаются как image blocks внутри tool_result).
Нет overhead абстракций LangChain/LlamaIndex.
Проще отлаживать и оптимизировать контекст вручную.

### Почему JPEG quality=80, device_scale_factor=1
device_scale_factor=2 рендерил в 2560x1600 — в 4x больше пикселей.
Это нагружало GPU и замедляло скриншоты.
При scale=1 + quality=80: чёткое изображение, низкая нагрузка.

### Почему Dual-Channel Perception
Только скриншот: агент не знает точные координаты кнопок.
Только a11y tree: агент не видит визуальный контекст и layout.
Вместе: скриншот для понимания страницы + дерево для точных кликов.
Исключает хардкодные селекторы полностью — агент адаптируется
к любому сайту динамически.

### Почему Hierarchical Planning
Без плана агент действует реактивно и может зациклиться.
Один лёгкий API вызов (~$0.001, без скриншота) в начале задачи.
План направляет выполнение но не ограничивает — агент отклоняется
когда нужно (Plan→Execute→Adapt).

### Почему auto-dismiss попапов убран
Автоматическое закрытие попапов мешало агенту работать с модальными окнами
(выбор адреса доставки, корзина, формы оплаты).
Агент сам решает что делать с попапом на основе скриншота и контекста задачи.
Это следует принципу Anthropic: агент должен самостоятельно определять
действия без заготовленных паттернов поведения.

### Управление контекстом
Скриншоты ротируются: в контексте хранятся только 2 последних.
Старые заменяются на "[screenshot removed]" для экономии токенов.
Сжатие при 100k символов предотвращает рост стоимости на длинных задачах.
Старые tool results в середине истории заменяются на "[result truncated]".
URL-based кэш a11y tree исключает повторный обход DOM без изменений страницы.

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
