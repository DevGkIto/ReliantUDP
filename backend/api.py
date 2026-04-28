from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi import HTTPException
from contextlib import asynccontextmanager
import os
import threading
import asyncio
import queue
from pydantic import BaseModel

from server import start_udp_server
from chaos import chaos_config
from event_queue import telemetry_queue
from client import run_udp_transfer 

# --- 1. GERENCIADOR DE WEBSOCKETS ---
class ConnectionManager:
    """Gerencia as conexões em tempo real ativas entre o backend e o frontend."""
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
        """Dispara a mesma mensagem (evento de rede) para todos os dashboards conectados."""
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except Exception:
                pass 

manager = ConnectionManager()

# --- 2. PONTE ASSÍNCRONA DE TELEMETRIA ---
async def bridge_telemetry_queues():
    """
    Conecta o mundo síncrono (threads UDP) com o mundo assíncrono (FastAPI).
    Drena a fila de eventos do protocolo e os transmite para a UI via WebSocket.
    """
    print("[*] API Bridge: Async telemetry drain started.")
    while True:
        try:
            event = telemetry_queue.get_nowait()
            await manager.broadcast(event.to_json())
            telemetry_queue.task_done()
        except queue.Empty:
            await asyncio.sleep(0.01)

# --- 3. CICLO DE VIDA DA APLICAÇÃO (LIFESPAN) ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Orquestra o que acontece ao ligar e desligar a API.
    Garante que o Servidor UDP e a Ponte de Telemetria rodem em background.
    """
    udp_thread = threading.Thread(target=start_udp_server, daemon=True)
    udp_thread.start()
    print("[*] API Bridge: UDP Server launched in background.")
    
    bridge_task = asyncio.create_task(bridge_telemetry_queues())
    
    yield

    bridge_task.cancel()
    print("[*] API Bridge: Shutting down.")

# --- 4. INICIALIZAÇÃO DA API E CORS ---
app = FastAPI(lifespan=lifespan)

# Permite que o frontend (Next.js na porta 3000) faça requisições para esta API sem ser bloqueado pelo navegador.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"], 
    allow_credentials=True,
    allow_methods=["*"], 
    allow_headers=["*"],
)

# --- 5. ROTAS (ENDPOINTS) ---
@app.websocket("/api/ws")
async def websocket_endpoint(websocket: WebSocket):
    """Endpoint onde o frontend se conecta para receber a telemetria ao vivo."""
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
    """Permite alterar dinamicamente a taxa de perda de pacotes (Chaos Injector)."""
    chaos_config.set_drop_rate(req.drop_rate)
    return {"status": "success", "new_drop_rate": chaos_config.get_drop_rate()}

class StartTransferRequest(BaseModel):
    session_id: str

@app.post("/api/start-transfer")
async def start_transfer(req: StartTransferRequest):
    """
    We use a native Daemon Thread instead of BackgroundTasks.
    This guarantees the OS will instantly kill the transfer if you hit CTRL+C.
    """
    client_thread = threading.Thread(
        target=run_udp_transfer, 
        args=(req.session_id,), 
        daemon=True
    )
    client_thread.start()
    
    return {
        "status": "success", 
        "message": f"UDP transfer pipeline initiated for session {req.session_id}"
    }

@app.get("/api/download/{session_id}")
async def download_file(session_id: str):
    """
    Recupera o arquivo finalizado. 
    Usa caminhos absolutos para evitar problemas de diretório dentro do container Docker.
    """
    base_dir = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(base_dir, f"received_{session_id}_test.txt")
    
    print(f"[*] API Download requested. Looking for: {file_path}")
    
    if not os.path.exists(file_path):
        print(f"[-] File not found! Files currently in {base_dir}: {os.listdir(base_dir)}")
        raise HTTPException(status_code=404, detail="File not found. Transfer may not be complete.")
    
    return FileResponse(
        path=file_path, 
        filename=f"telemetry_payload_{session_id[:8]}.txt", # Nome limpo sugerido ao usuário na hora de salvar
        media_type='text/plain'
    )