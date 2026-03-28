TOOL_DEFINITIONS = [
    {
        "name": "get_page_state",
        "description": (
            "Primary observation tool. Returns: (1) screenshot as JPEG image, "
            "(2) list of up to 25 interactive elements with bbox coordinates, "
            "(3) current URL. Call this after every navigation or click to see "
            "what changed. If an element you need is not in the list, it may be "
            "outside the viewport — use scroll() then call get_page_state() again."
        ),
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "navigate",
        "description": (
            "Navigate to a URL. Always include the full URL with https://. "
            "After navigation, call get_page_state() to verify the page loaded correctly. "
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
            "After clicking, always call get_page_state() to verify the result. "
            "If click has no effect, the element may be obscured — try scrolling first. "
            "Returns current URL after click. If URL changed, page navigated. "
            "Call get_page_state() to see the updated page."
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
        "description": "Scroll the page at the given coordinates. Use positive delta_y to scroll down, negative to scroll up.",
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
            "Wait only when you see a loading indicator or spinner in the screenshot. "
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
