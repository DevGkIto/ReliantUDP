# Real-Time ARQ Telemetry & Chaos Platform

A full-stack, distributed system demonstrating a custom Reliable UDP (Stop-and-Wait ARQ) protocol, real-time telemetry streaming, and server-side chaos engineering. Developed as a capstone systems engineering project for the Computer Networks curriculum at the Federal Technological University of Paraná (UTFPR).

## 🚀 Architecture
This project bridges low-level network threading with high-speed asynchronous UI updates:
* **Protocol Layer:** Custom Stop-and-Wait ARQ engine over raw UDP (`socket`).
* **Async Bridge:** A FastAPI `asyncio` seam that safely drains synchronous thread queues without blocking the web server.
* **Real-Time Tunnel:** Fan-out WebSocket manager broadcasting binary state as JSON.
* **Frontend:** Next.js / React dashboard visualizing packet state machines at 60fps.
* **Orchestration:** Fully containerized with Docker & Docker Compose.

## 🛠️ Quick Start (Docker)
Ensure Docker is installed, then run the entire stack with one command:
```bash
docker-compose up --build