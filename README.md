# SkyGate API Scheduler

SkyGate is a high-performance API scheduling and monitoring system with a premium, glassmorphic dashboard. It allows you to map target environments, schedule requests using interval or cron expressions, and monitor performance in real-time.

---

## 🚀 Getting Started

### Prerequisites
- Docker & Docker Compose
- Node.js (v18+) & Python (3.11+) if running locally

### 🐳 Quick Start with Docker
The easiest way to get SkyGate running is using Docker Compose:

```bash
# Clone the repository and navigate to the root
cd api-scheduler

# Build and start the services
sudo docker compose up --build
```

- **Frontend:** [http://localhost:3000](http://localhost:3000)
- **Backend:** [http://localhost:8000](http://localhost:8000)
- **API Docs:** [http://localhost:8000/docs](http://localhost:8000/docs)

---

## 🛠️ Local Development

### 1. Backend Setup
```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

### 2. Frontend Setup
```bash
cd frontend
npm install
npm run dev
```

The frontend will be available at [http://localhost:3000](http://localhost:3000).

---

## 🧠 Technical Architecture & Decisions

Below is a breakdown of the technical decisions, gotchas, and assumptions made across the project:

### 1. The Scheduling Engine (Resilience vs. Memory)
*   **Persistence:** We use `AsyncIOScheduler` with an in-memory job store.
*   **Assumption:** We assume long-lived backend processes. If the container restarts, active jobs are synced from the database on startup.
*   **Edge Case Capture:** Uses `replace_existing=True` to prevent duplicate job IDs across service reloads.

### 2. Infrastructure & Data Integrity
*   **Database:** Powered by **SQLite** with the `aiosqlite` wrapper for asynchronous operations.
*   **Volume Strategy:** Uses directory-based Docker volumes (`/app/data`) for robust persistence and to avoid file-locking conflicts between host and container.
*   **Schema Management:** Designed for rapid iteration. Current model changes are applied by initializing a fresh DB, with planning for Alembic migrations for production scaling.

### 3. API Communication (Performance & Safety)
*   **Timeout Safety:** Hard 30s timeout on all outgoing requests via `httpx`.
*   **Memory Protection:** capturse and caps response bodies at 1000 characters to prevent database bloating, while maintaining high-performance streaming for the execution worker.
*   **Validation:** Strict JSON header validation on both frontend (UI) and backend (Pydantic models).

### 4. Frontend Optimization
*   **Polling Engine:** Optimized 5-second polling refreshes the dashboard with real-time metrics.
*   **Styling:** Fully migrated to **Tailwind CSS v4** engine for high-performance JIT styling and modern CSS features like glassmorphism.
*   **Type Safety:** Strict TypeScript adherence across the entire data layer to prevent runtime failures.

---

## 📁 Project Structure
- `/backend`: FastAPI service, APScheduler logic, and SQLite data layer.
- `/frontend`: Next.js 16 (App Router) with Tailwind CSS v4.
- `docker-compose.yml`: Orchestration for both services.
