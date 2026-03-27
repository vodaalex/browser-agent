TOOL_DEFINITIONS = [
    {
        "name": "get_page_state",
        "description": (
            "MAIN observation tool. Call this at the start of every step. "
            "Returns a screenshot of the current page, a list of interactive elements "
            "with their bounding boxes, and the current URL. "
            "Use the screenshot for visual context and the elements list for precise click coordinates."
        ),
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "screenshot",
        "description": "Take a screenshot of the current page to see its current state visually.",
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "navigate",
        "description": "Navigate to a URL. Use this to go to a specific website.",
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
            "Click at the given absolute coordinates on the page. "
            "To click an element from the elements list, use its bbox center: "
            "x = bbox[0] + bbox[2]/2, y = bbox[1] + bbox[3]/2."
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
            "Type text into the currently focused element. "
            "Click the input field first, then call this to type."
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
        "description": "Press a keyboard key. Common keys: Enter, Tab, Escape, ArrowDown, ArrowUp, Backspace, Delete, Space.",
        "input_schema": {
            "type": "object",
            "properties": {
                "key": {
                    "type": "string",
                    "description": "Key name, e.g. Enter, Tab, Escape, ArrowDown",
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
        "description": "Wait for dynamic content to load. Maximum 5000ms.",
        "input_schema": {
            "type": "object",
            "properties": {
                "milliseconds": {
                    "type": "integer",
                    "description": "How long to wait in milliseconds (max 5000)",
                }
            },
            "required": ["milliseconds"],
        },
    },
    {
        "name": "ask_user",
        "description": (
            "Ask the user for information you need to complete the task, "
            "such as login credentials, personal information, or clarification. "
            "The agent will pause and wait for the user's response."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "question": {
                    "type": "string",
                    "description": "The question to ask the user",
                }
            },
            "required": ["question"],
        },
    },
    {
        "name": "task_complete",
        "description": (
            "Call this when the task is fully completed. "
            "Provide a clear summary of what was accomplished."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "report": {
                    "type": "string",
                    "description": "Detailed report of what was done and the outcome",
                }
            },
            "required": ["report"],
        },
    },
]
