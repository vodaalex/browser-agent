import asyncio
import json
import os
import re
from typing import Callable, Awaitable
from urllib.parse import urlparse

import anthropic

from browser import BrowserManager
from prompts import SYSTEM_PROMPT
from tools import TOOL_DEFINITIONS

MAX_SCREENSHOTS_IN_CONTEXT = 2
COMPRESS_THRESHOLD = 200_000
MAX_STEPS = 25


def get_action_description(tool: str, args: dict) -> str:
    if tool == "navigate":
        url = args.get("url", "")
        try:
            domain = urlparse(url).netloc or url[:40]
        except Exception:
            domain = url[:40]
        return f"Navigating to {domain}"
    elif tool == "click":
        return f"Clicking at ({args.get('x', 0)}, {args.get('y', 0)})"
    elif tool == "type_text":
        text = args.get("text", "")
        preview = text[:25] + "…" if len(text) > 25 else text
        return f'Typing "{preview}"'
    elif tool in ("get_page_state", "screenshot"):
        return "Analyzing page state"
    elif tool == "wait":
        return f"Waiting {args.get('milliseconds', 0)}ms"
    elif tool == "scroll":
        delta = args.get("delta_y", 0)
        direction = "down" if delta > 0 else "up"
        return f"Scrolling {direction}"
    elif tool == "press_key":
        return f"Pressing {args.get('key', '')}"
    elif tool == "ask_user":
        q = args.get("question", "")
        return f"Asking: {q[:40]}…" if len(q) > 40 else f"Asking: {q}"
    elif tool == "task_complete":
        return "Completing task"
    return tool


class BrowserAgent:
    def __init__(
        self,
        browser: BrowserManager,
        send_event: Callable[[dict], Awaitable[None]],
        wait_for_user: Callable[[], Awaitable[str]],
    ):
        self.browser = browser
        self.send_event = send_event
        self.wait_for_user = wait_for_user
        self.client = anthropic.AsyncAnthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        self.messages: list[dict] = []
        self.model = "claude-sonnet-4-5"
        self.max_tokens = 1024
        self._running = False
        self._step = 0
        self._last_page_state_step = -1
        self._cached_page_state = None
        self._url_history: list[str] = []

    async def _create_plan(self, task: str) -> list[str]:
        """One cheap API call (no screenshot) to outline 3-5 high-level steps."""
        try:
            response = await self.client.messages.create(
                model=self.model,
                max_tokens=300,
                system=(
                    "You are a planning agent. Given a browser task, "
                    "output a JSON array of 3-5 high-level steps to accomplish it. "
                    "Steps should be abstract goals, not specific actions. "
                    'Example: ["Navigate to hh.ru", "Search for AI engineer vacancies", '
                    '"Open first 3 relevant results", "Apply with cover letter"]\n'
                    "Output ONLY a raw JSON array. No markdown, no explanation."
                ),
                messages=[{"role": "user", "content": f"Task: {task}"}],
            )
            text = next((b.text for b in response.content if b.type == "text"), "[]")
            # Strip markdown code fences if present
            text = text.strip()
            m = re.search(r'\[.*\]', text, re.DOTALL)
            if m:
                text = m.group(0)
            plan = json.loads(text)
            return plan if isinstance(plan, list) else []
        except Exception:
            return []

    async def run(self, task: str):
        self._running = True
        self._step = 0
        self._last_page_state_step = -1
        self._cached_page_state = None
        self._url_history = []

        # ── Hierarchical planning ────────────────────────────────────
        plan = await self._create_plan(task)

        if plan:
            await self.send_event({"type": "plan", "steps": plan})
            plan_text = "\n".join(f"{i + 1}. {s}" for i, s in enumerate(plan))
            self.messages = [{
                "role": "user",
                "content": (
                    f"Task: {task}\n\n"
                    f"Your plan:\n{plan_text}\n\n"
                    "Now execute this plan step by step."
                ),
            }]
        else:
            self.messages = [{"role": "user", "content": task}]

        await self.send_event({"type": "thought", "content": f"Starting task: {task}"})

        try:
            while self._running:
                self._step += 1
                await self.send_event({"type": "step", "step": self._step})

                # ── Max steps guard ─────────────────────────────────────────
                if self._step > MAX_STEPS:
                    await self.send_event({
                        "type": "ask_user",
                        "question": (
                            f"I've taken {MAX_STEPS} steps. "
                            "Should I continue or stop? (reply 'continue' or 'stop')"
                        ),
                    })
                    answer = await self.wait_for_user()
                    if any(w in answer.lower() for w in ("stop", "нет", "no", "quit")):
                        break
                    self._step = 0  # reset counter, keep going

                # ── Main Claude call ────────────────────────────────────────
                response = await self.client.messages.create(
                    model=self.model,
                    max_tokens=self.max_tokens,
                    system=SYSTEM_PROMPT,
                    tools=TOOL_DEFINITIONS,
                    messages=self.messages,
                )

                self.messages.append({"role": "assistant", "content": response.content})

                for block in response.content:
                    if block.type == "text" and block.text.strip():
                        await self.send_event({"type": "thought", "content": block.text})

                if response.stop_reason == "end_turn":
                    await self.send_event({"type": "complete", "report": "Task finished."})
                    break

                if response.stop_reason != "tool_use":
                    break

                tool_results = []
                stop_after = False

                for block in response.content:
                    if block.type != "tool_use":
                        continue

                    tool_name = block.name
                    tool_input = block.input

                    await self.send_event({
                        "type": "action",
                        "tool": tool_name,
                        "description": get_action_description(tool_name, tool_input),
                        "args": tool_input,
                    })

                    if tool_name == "task_complete":
                        report = tool_input.get("report", "Task completed.")
                        await self.send_event({"type": "complete", "report": report})
                        tool_results.append(self._make_tool_result(block.id, {"success": True}))
                        stop_after = True
                        break

                    elif tool_name == "ask_user":
                        question = tool_input.get("question", "")
                        await self.send_event({"type": "ask_user", "question": question})
                        answer = await self.wait_for_user()
                        tool_results.append(self._make_tool_result(block.id, {"answer": answer}))

                    else:
                        result_content = await self._execute_browser_tool(tool_name, tool_input)

                        # Send action_result for side-effect tools (not page observation)
                        if tool_name not in ("get_page_state", "screenshot"):
                            is_error = False
                            detail = ""
                            if isinstance(result_content, str):
                                try:
                                    parsed = json.loads(result_content)
                                    is_error = "error" in parsed
                                    detail = (
                                        str(parsed.get("error", ""))[:60]
                                        if is_error
                                        else parsed.get("url", "")
                                    )
                                except Exception:
                                    pass
                            await self.send_event({
                                "type": "action_result",
                                "tool": tool_name,
                                "result": "error" if is_error else "success",
                                "detail": detail,
                            })

                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": result_content,
                        })

                if tool_results:
                    self.messages.append({"role": "user", "content": tool_results})
                    self._maybe_compress_context()

                # ── Stuck detection ─────────────────────────────────────────
                if len(self._url_history) >= 4:
                    recent = self._url_history[-4:]
                    if len(set(recent)) == 1 and recent[0] not in ("about:blank", ""):
                        self._url_history = []  # reset to avoid repeated trigger
                        await self.send_event({
                            "type": "thought",
                            "content": "Detected: same page for 4+ observations. Asking for guidance.",
                        })
                        await self.send_event({
                            "type": "ask_user",
                            "question": "I seem to be stuck on the same page. Can you help me proceed?",
                        })
                        answer = await self.wait_for_user()
                        self.messages.append({
                            "role": "user",
                            "content": f"User guidance: {answer}",
                        })

                if stop_after:
                    break

        except asyncio.CancelledError:
            pass
        except anthropic.APIError as e:
            await self.send_event({"type": "error", "message": f"API error: {e.message}"})
        except Exception as e:
            await self.send_event({"type": "error", "message": str(e)})
        finally:
            self._running = False

    async def _execute_browser_tool(self, name: str, args: dict) -> list | str:
        try:
            if name in ("get_page_state", "screenshot"):
                # Throttle: return cached state if called within 2 steps (after first)
                if (
                    self._step - self._last_page_state_step < 2
                    and self._step > 1
                    and self._cached_page_state is not None
                ):
                    return self._cached_page_state

                self._last_page_state_step = self._step
                state = await self.browser.get_page_state()
                self._url_history.append(state["url"])

                result = [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": "image/jpeg",
                            "data": state["screenshot"],
                        },
                    },
                    {
                        "type": "text",
                        "text": json.dumps(
                            {"url": state["url"], "elements": state["elements"]},
                            ensure_ascii=False,
                        ),
                    },
                ]
                self._cached_page_state = result
                return result

            elif name == "navigate":
                result = await self.browser.navigate(args["url"])
                self._cached_page_state = None  # page changed
                return json.dumps(result)

            elif name == "click":
                result = await self.browser.click(args["x"], args["y"])
                self._cached_page_state = None
                return json.dumps(result)

            elif name == "type_text":
                result = await self.browser.type_text(args["text"])
                return json.dumps(result)

            elif name == "press_key":
                result = await self.browser.press_key(args["key"])
                self._cached_page_state = None
                return json.dumps(result)

            elif name == "scroll":
                result = await self.browser.scroll(args["x"], args["y"], args["delta_y"])
                return json.dumps(result)

            elif name == "wait":
                result = await self.browser.wait(args["milliseconds"])
                return json.dumps(result)

            else:
                return json.dumps({"error": f"Unknown tool: {name}"})

        except Exception as e:
            return json.dumps({"error": str(e)})

    def _make_tool_result(self, tool_use_id: str, data: dict) -> dict:
        return {
            "type": "tool_result",
            "tool_use_id": tool_use_id,
            "content": json.dumps(data),
        }

    def _maybe_compress_context(self):
        context_size = sum(len(json.dumps(m, default=str)) for m in self.messages)
        if context_size < COMPRESS_THRESHOLD:
            return

        screenshot_count = 0
        # Walk backwards to keep the most recent screenshots
        for msg in reversed(self.messages):
            if msg["role"] == "user":
                content = msg.get("content", [])
                if isinstance(content, list):
                    for i, block in enumerate(content):
                        if isinstance(block, dict) and block.get("type") == "tool_result":
                            tr_content = block.get("content", "")
                            if isinstance(tr_content, list):
                                has_img = any(
                                    b.get("type") == "image"
                                    for b in tr_content
                                    if isinstance(b, dict)
                                )
                                if has_img:
                                    screenshot_count += 1
                                    if screenshot_count > MAX_SCREENSHOTS_IN_CONTEXT:
                                        text_blocks = [
                                            b for b in tr_content
                                            if isinstance(b, dict) and b.get("type") == "text"
                                        ]
                                        content[i] = {
                                            **block,
                                            "content": text_blocks + [
                                                {"type": "text", "text": "[screenshot removed]"}
                                            ],
                                        }
