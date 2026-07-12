# AnomalyPulse — Real-Time Anomaly Detection Engine

A production-grade streaming anomaly detection system that ingests time-series metrics, runs them through an ensemble of 4 detection algorithms in real-time, and surfaces anomalies via a live dashboard with WebSocket streaming.

## Why It Matters

Traditional threshold-based alerting misses subtle degradations and produces excessive false positives. AnomalyPulse uses statistical and ML-based detectors in an ensemble configuration — each detector votes independently, and the ensemble resolves disagreements. This catches anomalies that any single method would miss while suppressing noise.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Frontend (React/TS)                       │
│  ┌───────────┐ ┌──────────────┐ ┌──────────┐ ┌──────────────┐  │
│  │ StatsCards │ │ MetricChart  │ │AlertPanel│ │AnomalyTimeln │  │
│  └─────┬─────┘ └──────┬───────┘ └────┬─────┘ └──────┬───────┘  │
│        └───────────────┴──────────────┴──────────────┘          │
│                         WebSocket + REST                         │
└──────────────────────────────┬──────────────────────────────────┘
                               │
┌──────────────────────────────┴──────────────────────────────────┐
│                     Backend (FastAPI/Python)                      │
│                                                                  │
│  ┌──────────┐    ┌──────────────────┐    ┌───────────────────┐  │
│  │ Ingest   │───▶│ Detection Service │───▶│ Streaming Manager │  │
│  │ API      │    │                  │    │ (WebSocket)       │  │
│  └──────────┘    │  ┌────────────┐  │    └───────────────────┘  │
│                  │  │  Z-Score   │  │                            │
│  ┌──────────┐    │  │  EWMA      │  │    ┌───────────────────┐  │
│  │Simulator │───▶│  │  IForest   │  │───▶│  Alert Evaluator  │  │
│  │          │    │  │  Percentile│  │    └───────────────────┘  │
│  └──────────┘    │  │  Ensemble  │  │                            │
│                  │  └────────────┘  │    ┌───────────────────┐  │
│                  └──────────────────┘    │  SQLite Storage    │  │
│                                          └───────────────────┘  │
└──────────────────────────────────────────────────────────────────┘
```

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.11+, FastAPI, Uvicorn, aiosqlite |
| Detection | NumPy, scikit-learn (Isolation Forest) |
| Frontend | React 19, TypeScript, Vite, Zustand |
| Charts | Recharts |
| Transport | WebSocket (real-time), REST (config/history) |
| Storage | SQLite (async) |

## Detection Algorithms

### Z-Score
Statistical detector using rolling mean and standard deviation. Flags points beyond ±σ threshold (default 3.0). Best for normally distributed metrics.

### EWMA (Exponentially Weighted Moving Average)
Tracks a smoothed average with configurable decay (α=0.25). Detects deviations from the weighted trend. Reacts faster to recent changes than Z-Score.

### Isolation Forest
ML-based detector from scikit-learn. Builds random trees and isolates anomalies by path length. Catches multivariate and non-linear anomalies that statistical methods miss. Retrains periodically (every 30 points by default).

### Percentile
Flags values outside configurable percentile bounds (default P5–P95) over a rolling window. Simple, robust, distribution-agnostic.

### Ensemble
Combines all 4 detectors via configurable voting. Modes:
- **majority** — anomaly if ≥50% of detectors agree (default)
- **any** — anomaly if any single detector flags
- **all** — anomaly only if all detectors agree

## Quick Start

### Backend
```bash
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
bash run.sh
# → http://localhost:8080
```

### Frontend
```bash
cd frontend
npm install
npm run dev
# → http://localhost:5173
```

### Both at once
```bash
chmod +x start.sh
./start.sh
```

## API Reference

### Ingest
| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/v1/ingest` | Ingest a single metric data point |
| `POST` | `/api/v1/ingest/batch` | Ingest a batch of metric data points |

### Metrics
| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/v1/metrics` | List known metrics |
| `GET` | `/api/v1/metrics/{name}/history` | Get metric history with time range |

### Anomalies
| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/v1/anomalies` | List detected anomalies (filterable) |
| `GET` | `/api/v1/anomalies/stats` | Anomaly statistics summary |

### Detectors
| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/v1/detectors` | List all detector configurations |
| `PUT` | `/api/v1/detectors/{name}` | Update detector parameters |

### Alerts
| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/v1/alerts` | List alert rules |
| `POST` | `/api/v1/alerts` | Create alert rule |
| `PUT` | `/api/v1/alerts/{id}` | Update alert rule |
| `DELETE` | `/api/v1/alerts/{id}` | Delete alert rule |

### Simulator
| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/v1/simulator/start` | Start metric simulator |
| `POST` | `/api/v1/simulator/stop` | Stop simulator |
| `GET` | `/api/v1/simulator/status` | Get simulator status |

### Health
| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/v1/health` | Health check |
| `GET` | `/api/v1/health/detailed` | Detailed health with DB + detector status |

## WebSocket Events

Connect to `ws://localhost:8080/ws`

| Event | Direction | Description |
|-------|-----------|-------------|
| `metric` | Server → Client | New metric data point received |
| `anomaly` | Server → Client | Anomaly detected by ensemble |
| `alert` | Server → Client | Alert rule triggered |
| `health` | Server → Client | Periodic health heartbeat |

## Simulator Scenarios

Start via `POST /api/v1/simulator/start` with `scenario` field:

| Scenario | Description |
|----------|-------------|
| `normal` | Stable metrics with minor noise |
| `spike` | Periodic sharp spikes |
| `drift` | Gradual baseline drift over time |
| `chaos` | Random anomalies across all metrics |
| `cpu_stress` | Simulated CPU saturation pattern |

Default metrics: `cpu.usage`, `memory.usage`, `disk.io`, `network.bytes`, `api.latency`

## Configuration

Configured via `app/config.py`:

| Parameter | Default | Description |
|-----------|---------|-------------|
| `zscore_window` | 60 | Z-Score rolling window size |
| `zscore_sigma` | 3.0 | Z-Score sigma threshold |
| `ewma_alpha` | 0.25 | EWMA decay factor |
| `ewma_k` | 2.5 | EWMA deviation multiplier |
| `iforest_window` | 120 | Isolation Forest window |
| `iforest_contamination` | 0.03 | Expected anomaly ratio |
| `iforest_retrain_every` | 30 | Retrain interval (points) |
| `percentile_lower` | 0.05 | Lower percentile bound |
| `percentile_upper` | 0.95 | Upper percentile bound |
| `ensemble_mode` | majority | Voting: majority / any / all |
| `ingest_per_sec` | 50 | Ingest rate limit |

## Project Structure

```
anomalypulse/
├── start.sh                    # Launch backend + frontend
├── README.md
├── backend/
│   ├── run.sh                  # Backend launcher
│   ├── requirements.txt
│   └── app/
│       ├── main.py             # FastAPI app + lifespan
│       ├── config.py           # Pydantic settings
│       ├── database.py         # Async SQLite
│       ├── simulator.py        # Metric simulator engine
│       ├── api/
│       │   ├── alerts.py       # Alert CRUD endpoints
│       │   ├── anomalies.py    # Anomaly query endpoints
│       │   ├── detectors.py    # Detector config endpoints
│       │   ├── health.py       # Health check endpoints
│       │   ├── ingest.py       # Metric ingestion endpoints
│       │   ├── metrics.py      # Metric history endpoints
│       │   ├── simulator.py    # Simulator control endpoints
│       │   └── websocket.py    # WebSocket handler
│       ├── alerts/
│       │   └── evaluator.py    # Alert rule evaluation
│       ├── detectors/
│       │   ├── base.py         # Abstract detector interface
│       │   ├── zscore.py       # Z-Score detector
│       │   ├── ewma.py         # EWMA detector
│       │   ├── isolation_forest.py  # Isolation Forest detector
│       │   ├── percentile.py   # Percentile detector
│       │   └── ensemble.py     # Ensemble orchestrator
│       ├── models/
│       │   └── schemas.py      # Pydantic request/response models
│       ├── repositories/
│       │   ├── alert_repo.py   # Alert persistence
│       │   ├── anomaly_repo.py # Anomaly persistence
│       │   ├── detector_repo.py# Detector config persistence
│       │   └── metrics_repo.py # Metric persistence
│       ├── services/
│       │   ├── detection_service.py  # Detection orchestration
│       │   └── ingestion_service.py  # Ingestion pipeline
│       └── streaming/
│           └── manager.py      # WebSocket broadcast manager
├── frontend/
│   ├── package.json
│   ├── vite.config.ts
│   ├── index.html
│   └── src/
│       ├── main.tsx
│       ├── App.tsx
│       ├── index.css
│       ├── types/index.ts
│       ├── lib/
│       │   ├── api.ts          # REST API client
│       │   └── websocket.ts    # WebSocket client
│       ├── hooks/
│       │   ├── useApi.ts       # API hook
│       │   └── useWebSocket.ts # WebSocket hook
│       ├── stores/
│       │   ├── appStore.ts     # App state (Zustand)
│       │   ├── alertStore.ts   # Alert state
│       │   └── metricsStore.ts # Metrics state
│       └── components/
│           ├── Layout.tsx
│           ├── Sidebar.tsx
│           ├── StatsCards.tsx
│           ├── MetricChart.tsx
│           ├── HealthBar.tsx
│           ├── AlertPanel.tsx
│           ├── DetectorConfig.tsx
│           └── AnomalyTimeline.tsx
```

## Screenshots

> *Screenshots to be added after deployment.*

---

Built as Production Loop 2 of the autonomous build pipeline.
