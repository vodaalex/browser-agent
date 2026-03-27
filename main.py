import asyncio
import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles

load_dotenv()

from browser import BrowserManager
from agent import BrowserAgent

browser = BrowserManager()


@asynccontextmanager
async def lifespan(app: FastAPI):
    await browser.start()
    print("Browser started.")
    yield
    await browser.stop()
    print("Browser stopped.")


app = FastAPI(lifespan=lifespan)
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/")
async def index():
    return FileResponse("static/index.html")


@app.get("/favicon.ico")
async def favicon():
    return Response(status_code=204)


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()

    user_reply_queue: asyncio.Queue[str] = asyncio.Queue()
    agent_task: asyncio.Task | None = None

    async def send_event(event: dict):
        try:
            await websocket.send_json(event)
        except Exception:
            pass

    async def wait_for_user() -> str:
        return await user_reply_queue.get()

    agent = BrowserAgent(
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
        pass
    except Exception:
        pass
    finally:
        if agent_task and not agent_task.done():
            agent_task.cancel()
            try:
                await agent_task
            except asyncio.CancelledError:
                pass


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
        log_level="info",
    )
