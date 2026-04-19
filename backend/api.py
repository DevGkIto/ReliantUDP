from fastapi import FastAPI, WebSocket, WebSocketDisconnect, BackgroundTasks # <-- Added BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import threading
import asyncio
import queue
from pydantic import BaseModel

from server import start_udp_server
from chaos import chaos_config
from event_queue import telemetry_queue
from client import run_udp_transfer # <-- NEW: Import our refactored client

# --- 1. THE WEBSOCKET MANAGER ---
class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        print(f"[*] WS: Client connected. Total: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
        print(f"[*] WS: Client disconnected. Total: {len(self.active_connections)}")

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except Exception:
                pass 

manager = ConnectionManager()
# --------------------------------

# --- 2. THE ASYNC BRIDGE ---
async def bridge_telemetry_queues():
    print("[*] API Bridge: Async telemetry drain started.")
    while True:
        try:
            event = telemetry_queue.get_nowait()
            await manager.broadcast(event.to_json())
            telemetry_queue.task_done()
        except queue.Empty:
            await asyncio.sleep(0.01)
# ---------------------------

# --- 3. LIFESPAN ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    udp_thread = threading.Thread(target=start_udp_server, daemon=True)
    udp_thread.start()
    print("[*] API Bridge: UDP Server launched in background.")
    
    bridge_task = asyncio.create_task(bridge_telemetry_queues())
    
    yield
    
    bridge_task.cancel()
    print("[*] API Bridge: Shutting down.")
# ----------------------------------------------------

# --- 4. APP INITIALIZATION & CORS ---
app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"], 
    allow_credentials=True,
    allow_methods=["*"], 
    allow_headers=["*"],
)
# ------------------------------------

# --- 5. ROUTES ---
@app.websocket("/api/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)

class ChaosUpdateRequest(BaseModel):
    drop_rate: int

@app.patch("/api/chaos")
async def update_chaos(req: ChaosUpdateRequest):
    chaos_config.set_drop_rate(req.drop_rate)
    return {"status": "success", "new_drop_rate": chaos_config.get_drop_rate()}

# --- NEW: STEP B START TRANSFER ENDPOINT ---
class StartTransferRequest(BaseModel):
    session_id: str

@app.post("/api/start-transfer")
async def start_transfer(req: StartTransferRequest, background_tasks: BackgroundTasks):
    """
    SaaS UX: The frontend commands the backend to start the UDP transfer
    natively in memory without blocking the API response.
    """
    # Fire and forget: Runs the UDP client loop in a background thread managed by FastAPI
    background_tasks.add_task(run_udp_transfer, req.session_id)
    
    return {
        "status": "success", 
        "message": f"UDP transfer pipeline initiated for session {req.session_id}"
    }
# -------------------------------------------

@app.get("/api/health")
async def health_check():
    return {"status": "online", "current_drop_rate": chaos_config.get_drop_rate()}