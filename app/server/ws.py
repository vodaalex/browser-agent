"""WebSocket endpoint — bridges the frontend UI with the AgentExecutor."""

from __future__ import annotations

import asyncio

from fastapi import WebSocket, WebSocketDisconnect

from app.log import logger


async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()

    # Lazy import to avoid circular dependency at module level
    from app.server.app import browser
    from app.agent.executor import AgentExecutor

    user_reply_queue: asyncio.Queue[str] = asyncio.Queue()
    agent_task: asyncio.Task | None = None

    async def send_event(event: dict):
        try:
            await websocket.send_json(event)
        except Exception:
            pass

    async def wait_for_user() -> str:
        return await user_reply_queue.get()

    agent = AgentExecutor(
        browser=browser,
        send_event=send_event,
        wait_for_user=wait_for_user,
    )

    try:
        while True:
            data = await websocket.receive_json()
            msg_type = data.get("type")

            if msg_type == "task":
                # Cancel any running agent task
                if agent_task and not agent_task.done():
                    agent_task.cancel()
                    try:
                        await agent_task
                    except asyncio.CancelledError:
                        pass
                # Clear pending user replies
                while not user_reply_queue.empty():
                    user_reply_queue.get_nowait()

                task_content = data.get("content", "")
                logger.info("New task: %s", task_content[:80])
                agent_task = asyncio.create_task(agent.run(task_content))

            elif msg_type == "user_reply":
                reply = data.get("content", "")
                await user_reply_queue.put(reply)

            elif msg_type == "stop":
                if agent_task and not agent_task.done():
                    agent_task.cancel()
                    try:
                        await agent_task
                    except asyncio.CancelledError:
                        pass
                await send_event({"type": "error", "message": "Stopped by user."})

    except WebSocketDisconnect:
        logger.info("WebSocket disconnected")
    except Exception as e:
        logger.error("WebSocket error: %s", e)
    finally:
        if agent_task and not agent_task.done():
            agent_task.cancel()
            try:
                await agent_task
            except asyncio.CancelledError:
                pass

