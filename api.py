from fastapi import FastAPI
from contextlib import asynccontextmanager
import threading
import asyncio
import queue
from pydantic import BaseModel

from server import start_udp_server
from chaos import chaos_config
from event_queue import telemetry_queue

async def bridge_telemetry_queues():
    """
    The Seam: Drains the synchronous threading queue 
    and brings events into the asyncio event loop.
    """
    print("[*] API Bridge: Async telemetry drain started.")
    while True:
        try:
            # 1. Non-blocking get! If empty, it immediately throws queue.Empty
            event = telemetry_queue.get_nowait()
            
            # 2. We are now safely in the async world!
            # For this block, we just print it to prove we have it.
            print(f" ASYNC WORLD CAUGHT: {event.to_json()}")
            
            telemetry_queue.task_done()
            
        except queue.Empty:
            # 3. If empty, yield control back to FastAPI for 10ms
            # This is the magic line that prevents the server from freezing.
            await asyncio.sleep(0.01)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 1. Boot the UDP server in a background THREAD
    udp_thread = threading.Thread(target=start_udp_server, daemon=True)
    udp_thread.start()
    print("[*] API Bridge: UDP Server launched in background.")
    
    # 2. Boot the Bridge in a background ASYNC TASK
    bridge_task = asyncio.create_task(bridge_telemetry_queues())
    
    yield # FastAPI handles web requests here
    
    bridge_task.cancel()
    print("[*] API Bridge: Shutting down.")

app = FastAPI(lifespan=lifespan)

class ChaosUpdateRequest(BaseModel):
    drop_rate: int

@app.patch("/api/chaos")
async def update_chaos(req: ChaosUpdateRequest):
    chaos_config.set_drop_rate(req.drop_rate)
    return {"status": "success", "new_drop_rate": chaos_config.get_drop_rate()}

@app.get("/api/health")
async def health_check():
    return {"status": "online", "current_drop_rate": chaos_config.get_drop_rate()}