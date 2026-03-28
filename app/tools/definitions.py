TOOL_DEFINITIONS = [
    {
        "name": "get_elements",
        "description": (
            "Fast observation tool. Returns interactive elements with coordinates "
            "and current URL — WITHOUT a screenshot. "
            "Use this after most actions when you already understand the page layout. "
            "Use get_page_state() instead only when you need to visually see the page "
            "for the first time, read text content not present in elements, "
            "or understand a complex visual layout."
        ),
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "get_page_state",
        "description": (
            "Visual observation tool. Returns a screenshot + interactive elements + URL. "
            "Use ONLY when you need to see the page visually: "
            "first visit to an unknown page, reading prices/text not in element labels, "
            "or understanding a complex layout. "
            "For all other cases use get_elements() — it is 5-10x faster."
        ),
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "navigate",
        "description": (
            "Navigate to a URL. Always include the full URL with https://. "
            "Returns the final URL and page title so you can verify the correct page loaded. "
            "After navigation call get_elements() to read interactive elements, "
            "or get_page_state() only if you need to visually inspect the layout. "
            "If the page requires login, call ask_user() for credentials."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "The full URL to navigate to, e.g. https://example.com",
                }
            },
            "required": ["url"],
        },
    },
    {
        "name": "click",
        "description": (
            "Click at absolute pixel coordinates. Compute center from bbox: "
            "x = bbox[0] + bbox[2]//2, y = bbox[1] + bbox[3]//2. "
            "Returns the URL after click — if it changed, the page navigated. "
            "After clicking call get_elements() to check the result. "
            "Use get_page_state() only when you need visual confirmation of the new state. "
            "If click has no effect, scroll to the element first and try again."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "x": {"type": "integer", "description": "X coordinate in pixels"},
                "y": {"type": "integer", "description": "Y coordinate in pixels"},
            },
            "required": ["x", "y"],
        },
    },
    {
        "name": "type_text",
        "description": (
            "Type text into the currently focused element. You must click the "
            "input field first to focus it, then call type_text(). For search fields, "
            "follow with press_key('Enter') to submit. If the field already has text, "
            "it will be appended — use press_key('Control+a') first to select all."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "text": {"type": "string", "description": "The text to type"}
            },
            "required": ["text"],
        },
    },
    {
        "name": "press_key",
        "description": "Press a keyboard key. Common keys: Enter, Tab, Escape, ArrowDown, ArrowUp, Backspace, Delete, Space, Control+a.",
        "input_schema": {
            "type": "object",
            "properties": {
                "key": {
                    "type": "string",
                    "description": "Key name, e.g. Enter, Tab, Escape, ArrowDown, Control+a",
                }
            },
            "required": ["key"],
        },
    },
    {
        "name": "scroll",
        "description": (
            "Scroll the page at the given coordinates. "
            "Positive delta_y scrolls down, negative scrolls up. "
            "After scrolling call get_elements() to see newly visible interactive elements."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "x": {
                    "type": "integer",
                    "description": "X coordinate of the scroll position",
                },
                "y": {
                    "type": "integer",
                    "description": "Y coordinate of the scroll position",
                },
                "delta_y": {
                    "type": "integer",
                    "description": "Scroll amount in pixels. Positive = down, negative = up",
                },
            },
            "required": ["x", "y", "delta_y"],
        },
    },
    {
        "name": "wait",
        "description": (
            "Wait when you know the page is still loading — for example after submitting "
            "a form that triggers a slow request, or when get_elements() keeps returning "
            "the same empty or partial state. "
            "Do NOT call wait() after navigate() or click() — they already wait for "
            "the page to stabilize. Maximum 3000ms."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "milliseconds": {
                    "type": "integer",
                    "description": "How long to wait in milliseconds (max 3000)",
                }
            },
            "required": ["milliseconds"],
        },
    },
    {
        "name": "type_and_submit",
        "description": (
            "Click an input field, type text, and press Enter to submit — "
            "all in a single step. Use for search boxes, forms, and any input "
            "where you need to type and immediately submit. "
            "When looking for specific products or content on any website, "
            "using this tool with a search box is faster and more reliable "
            "than navigating through menus or categories. "
            "Provide the center coordinates of the input field. "
            "More efficient than calling click + type_text + press_key separately."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "x": {"type": "integer", "description": "X coordinate of the input field center"},
                "y": {"type": "integer", "description": "Y coordinate of the input field center"},
                "text": {"type": "string", "description": "Text to type and submit"},
            },
            "required": ["x", "y", "text"],
        },
    },
    {
        "name": "go_back",
        "description": (
            "Navigate back to the previous page in browser history. "
            "Use this instead of navigate() when you want to return "
            "to the page you came from. Faster and more reliable than "
            "remembering and re-navigating to the previous URL."
        ),
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "ask_user",
        "description": (
            "Pause and ask the user for required information. Use when: "
            "login credentials are needed; "
            "delivery address or personal info is required; "
            "task is ambiguous and needs clarification; "
            "you are stuck after 3+ attempts on the same goal. "
            "Be specific about what information you need and why."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "question": {
                    "type": "string",
                    "description": "The specific question to ask the user",
                }
            },
            "required": ["question"],
        },
    },
    {
        "name": "task_complete",
        "description": (
            "Mark the task as done and provide a summary. Call this immediately "
            "when the goal is achieved — do not continue exploring. "
            "Write report as plain text without markdown symbols. "
            "First line: one-sentence summary. Then details with line breaks."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "report": {
                    "type": "string",
                    "description": "Plain-text report of what was accomplished. No markdown.",
                }
            },
            "required": ["report"],
        },
    },
]
