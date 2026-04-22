# Fazri Analyzer

![Fazri Analyzer Screenshot](https://cdn.hextasphere.com/hexta/ethos/screenshot-with-background.png)

A multi-tenant campus intelligence platform built as a pnpm monorepo with Turborepo. It combines a Next.js 16 dashboard, a dedicated Express/Better Auth service, a FastAPI ML engine with TensorFlow and graph analytics, and an InsightFace-powered face recognition microservice — all orchestrated via Docker Compose on a single-node on-premise deployment.

The platform ingests data from Hikvision RFID access-control readers and Aruba WiFi APs, fuses it with live camera feeds via go2rtc (RTSP/WebRTC), runs anomaly detection and occupancy forecasting, and surfaces everything through an interactive dashboard with an AI chat interface backed by Google Gemini 2.5 Flash / Vertex AI.

## 🎯 Product Demo

- **Demo Link**: [fazri.rayzrsole.com](https://fazri.rayzrsole.com)
- **Super Admin Credentials**: username: `admin` | password: `Ethos@123`
- **Student Credentials**: username: `E100000-E106999` | password: `Ethos@123`

---

## 🏆 Recognition

Fazri Analyzer was featured in two prestigious student innovation competitions:

| Event | Organizer | Description |
|-------|-----------|-------------|
| [Ethos Hackathons 2025](https://unstop.com/hackathons/ethos-hackathons-2025-iit-guwahati-1562001) | IIT Guwahati | Northeast India's largest hackathon - 48-hour offline event solving real-world problems sourced from government and industry partners |
| [i-Hack @ E-Summit](https://unstop.com/hackathons/i-hack-iit-bombay-1580510) | IIT Bombay E-Cell | GitLab Startup Accelerator track within Asia's largest student-run entrepreneurship conclave; teams build production-ready software demonstrating the full DevSecOps lifecycle |

---

## 🔧 CI/CD Pipeline (Jenkins + Proxmox)

The project uses **Jenkins** running on a self-hosted Proxmox VM as the CI/CD engine. All services are built and deployed locally on the same host - no external container registry is used.

### Pipeline Overview

```
Push to GitLab repo
       │
       ▼
Jenkins detects push via webhook
       │
       ▼
[Checkout] → [Environment Check] → [Set Environment]
       │
       ▼
[Detect Changes]  (git diff HEAD~1 HEAD)
  apps/api/**       → BUILD_BACKEND=true
  apps/auth/**      → BUILD_AUTH=true
  packages/**       → BUILD_AUTH=true  (shared @fazri/db)
  apps/deepface/**  → BUILD_DEEPFACE=true
  mediamtx/**       → BUILD_GO2RTC=true
  Jenkinsfile       → rebuild all
       │
       ▼
[Build Images] ────────────────── parallel ──────────────────
  fazri-analyzer-backend:{branch}-{sha}
  fazri-analyzer-auth:{branch}-{sha}
  fazri-deepface-server:{branch}-{sha}
  fazri-go2rtc:{branch}-{sha}          (staging only)
       │
       ▼
[Deploy] ────────────────────────── parallel ────────────────
  Backend     docker run -d on backend_fazri-network
  Auth        docker run -d on backend_fazri-network
  DeepFace    docker run -d on backend_fazri-network
  go2rtc      docker run -d (staging only)
  Simulators  Hikvision + Aruba simulators (staging only)
  ↓ health-check each container before proceeding
       │
       ▼
[Sentry Release]  ─────────────── parallel ──────────────────
  backend / auth / deepface releases finalized in Sentry
       │
       ▼
[Cleanup]  prune dangling images, remove old branch-tagged images
```

### Environments

| Branch | Environment | Backend port | Auth port |
|--------|-------------|-------------|-----------|
| `master` | production | `8000` | `4002` |
| any other | staging | `8001` | `4003` |

- **master** deploys to live production containers (`fazri-api`, `fazri-auth`, `deepface-server`)
- **feature branches** deploy to staging containers (`fazri-api-staging`, etc.) with simulators replacing real Hikvision/Aruba hardware

### Image Tagging

Images are tagged as `{sanitized-branch}-{7-char-sha}` (e.g. `master-abc1234f`). The `latest` tag is also applied on `master` builds. Old images for the same branch are pruned after each successful deploy.

### Credentials

All secrets (database URIs, API keys, auth tokens, sensor credentials) are stored as **Jenkins credentials** and injected as environment variables at container start time - never baked into images.

### Sentry Releases

After each successful deploy, `sentry-cli` creates a release for the affected service(s), associates commits via `--auto`, and marks the deploy environment (`production` or `staging`).

---

## ✨ Features

- **Entity Tracking & Analysis** — real-time movement timeline, cross-source identity resolution, activity pattern analysis, and fusion reports combining RFID, WiFi, and camera data
- **Multi-Tenancy** — organization-based data isolation via Better Auth; every API call is scoped to an active organization; org-level JWT tokens carry the organization context
- **Enterprise SSO** — OIDC and SAML 2.0 via `@better-auth/sso`; SSO providers are linked per-organization; users are auto-provisioned and added to the organization's member list on first login
- **Role-Based Access Control** — two independent RBAC layers: global roles (`SUPER_ADMIN`, `STAFF`, `FACULTY`, `STUDENT`) and org-level roles (`owner`, `admin`, `member`) with granular permissions across cameras, alerts, staff, face enrollment, webhooks, reports, and sensors
- **Face Recognition** — InsightFace `buffalo_l` model (SCRFD detector + ArcFace) for enrollment and identification; embeddings stored in pgvector with HNSW-indexed cosine similarity search; impossible-travel anomaly detection flags identities appearing in physically impossible locations
- **Camera Management** — RTSP stream registration, go2rtc relay for WebRTC browser delivery, per-camera zone assignment, live feed access from the dashboard
- **Zone Occupancy** — spatial zone definitions, real-time occupancy counts, occupancy forecasting with scikit-learn, dwell time analysis
- **Anomaly Detection** — pattern analysis engine with configurable severity scoring, impossible-travel detection across both face recognition and sensor data, alert deduplication via Redis cooldown
- **Alert Management** — full alert lifecycle: create, assign (proximity + workload weighted), acknowledge, escalate, and resolve; multi-channel notifications (SMTP email, Twilio SMS, Discord webhook, web push)
- **Graph Analysis** — Neo4j 5 movement relationship graph; co-presence analysis; path finding between zones; CCTV graph visualization
- **AI Chat** — conversational interface backed by Google Gemini 2.5 Flash / Vertex AI with tool-calling for entity lookups, occupancy queries, and alert summaries; conversation state stored in Redis
- **Admin Panel** — `SUPER_ADMIN` console for global user management, organization provisioning, session inspection, SSO provider configuration, and platform analytics
- **Webhooks** — outgoing webhooks with configurable event types, HMAC-SHA256 request signing, and retry logic with exponential backoff
- **Sensor Integration** — Hikvision ISAPI RFID access-control reader polling and Aruba AOS8 WiFi association polling; both include built-in simulators for development
- **Predictive Zone Forecast** — ML-powered future occupancy predictions for proactive resource allocation
- **Real-Time Data Tables** — TanStack Table for efficient large-dataset management across entities, alerts, events, and staff

---

## 🛠️ Tech Stack

### Frontend (`apps/web`)
| Technology | Version | Purpose |
|------------|---------|---------|
| [Next.js](https://nextjs.org/) | 16.2.3 | React Framework (App Router, Turbopack) |
| [React](https://react.dev/) | 19.2.4 | UI Library |
| [TypeScript](https://www.typescriptlang.org/) | 5.x | Type Safety |
| [Tailwind CSS](https://tailwindcss.com/) | 4.0 | Styling |
| [HeroUI](https://www.heroui.com/) | 2.8.x | Primary Component Library |
| [Radix UI](https://www.radix-ui.com/) | — | Headless Primitives |
| [shadcn/ui](https://ui.shadcn.com/) | — | Additional UI Components |
| [Framer Motion](https://www.framer.com/motion/) | 12.x | Animations |
| [TanStack Query](https://tanstack.com/query) | 5.x | Server State Management |
| [TanStack Table](https://tanstack.com/table) | 8.x | Data Tables |
| [Recharts](https://recharts.org/) | 2.15.4 | Analytics Charts |
| [Three.js](https://threejs.org/) + [@react-three/fiber](https://github.com/pmndrs/react-three-fiber) | 0.170 / 9.3 | 3D Visualization |
| [Better Auth](https://www.better-auth.com/) client | 1.5.4 | Auth (org, SSO, JWT, admin plugins) |
| [Axios](https://axios-http.com/) | 1.15 | HTTP Client |
| [Zod](https://zod.dev/) | 4.x | Schema Validation |
| [Sentry](https://sentry.io/) | 10.x | Error Tracking |

### Auth Service (`apps/auth`)
| Technology | Version | Purpose |
|------------|---------|---------|
| [Express.js](https://expressjs.com/) | 4.x | HTTP Server |
| [Better Auth](https://www.better-auth.com/) | 1.5.4 | Auth Framework |
| username plugin | — | Username/password login |
| jwt plugin (RS256) | — | Signed JWT token issuance |
| organization plugin | — | Multi-tenant org management |
| admin plugin | — | Global user/session management |
| [@better-auth/sso](https://www.better-auth.com/docs/plugins/sso) | 1.5.4 | OIDC + SAML 2.0 SSO |
| [Prisma](https://www.prisma.io/) | 6.x | Database ORM (`@fazri/db` workspace package) |
| [Sentry](https://sentry.io/) | 8.x | Error Tracking |

### Backend API (`apps/api`)
| Technology | Version | Purpose |
|------------|---------|---------|
| [FastAPI](https://fastapi.tiangolo.com/) | 0.118.0 | API Framework |
| [Python](https://www.python.org/) | 3.10+ | Language |
| [Uvicorn](https://www.uvicorn.org/) | 0.37 | ASGI Server |
| [SQLAlchemy](https://www.sqlalchemy.org/) | 2.0 | PostgreSQL ORM |
| [TensorFlow](https://www.tensorflow.org/) | 2.20.0 | Machine Learning Models |
| [scikit-learn](https://scikit-learn.org/) | 1.7.2 | Forecasting & ML Utilities |
| [face-recognition](https://github.com/ageitgey/face_recognition) | 1.3.0 | Supplementary Face Matching |
| [neo4j](https://neo4j.com/) Python Driver | 6.0 | Graph Database Client |
| [Redis](https://redis.io/) | 6.4 | Alert Cooldown & Chat Sessions |
| [Pandas](https://pandas.pydata.org/) | 2.3 | Data Manipulation |
| [Google Generative AI](https://ai.google.dev/) / [Vertex AI](https://cloud.google.com/vertex-ai) | — | Gemini 2.5 Flash Chatbot |
| Twilio | — | SMS Notifications |
| [Sentry](https://sentry.io/) | 2.24 | Error Tracking & Performance |

### Face Recognition Service (`apps/deepface`)
| Technology | Version | Purpose |
|------------|---------|---------|
| [FastAPI](https://fastapi.tiangolo.com/) | 0.115 | API Framework |
| [InsightFace](https://github.com/deepinsight/insightface) (`buffalo_l`) | 0.7.3+ | SCRFD Face Detection + ArcFace Recognition |
| [ONNX Runtime](https://onnxruntime.ai/) | — | Model Inference Engine |
| [pgvector](https://github.com/pgvector/pgvector) Python | 0.3.6 | Embedding Storage & HNSW Cosine Search |
| [OpenCV](https://opencv.org/) | 4.11 | Image Processing |
| [Sentry](https://sentry.io/) | 2.24 | Error Tracking |

### Databases
| Technology | Version | Purpose |
|------------|---------|---------|
| [PostgreSQL](https://www.postgresql.org/) | 15 | Primary Application Database (Prisma-managed) |
| [pgvector/PostgreSQL](https://github.com/pgvector/pgvector) | pg17 | Face Embedding Storage (HNSW index) |
| [Neo4j](https://neo4j.com/) | 5 | Movement Graph Analysis |
| [Redis](https://redis.io/) | 7 | Session Cache, Alert Cooldown, Chat History |

### DevOps & Infrastructure
| Technology | Version | Purpose |
|------------|---------|---------|
| [Docker Compose](https://docs.docker.com/compose/) | v2 | 9-service production stack |
| [Turborepo](https://turbo.build/) | 2.9 | Monorepo Build Orchestration |
| [pnpm](https://pnpm.io/) | 10.32 | Package Manager & Workspaces |
| [Nginx](https://nginx.org/) | alpine | Reverse Proxy + SSL Termination |
| [go2rtc](https://github.com/AlexxIT/go2rtc) | v1.9.7 | RTSP Relay + WebRTC Browser Delivery |
| [Jenkins](https://www.jenkins.io/) | — | CI/CD Pipeline (path-based parallel builds) |
| [Proxmox VE](https://www.proxmox.com/) | — | Self-hosted Deployment Target (VM host) |
| [GitLab](https://gitlab.com/) | — | Source Control & Merge Requests |
| [Sentry](https://sentry.io/) | — | Cross-service Error Tracking & Releases |

---

## 🚀 Getting Started

### Prerequisites
- [Node.js](https://nodejs.org/) v20+
- [pnpm](https://pnpm.io/) v10+
- [Python](https://www.python.org/) 3.10+
- [Docker](https://www.docker.com/) with Compose v2

### 1. Clone & Install

```bash
git clone https://gitlab.com/fazri8594547/fazri-analyzer.git
cd fazri-analyzer
cp .env.example .env          # fill in all required values
pnpm install                  # installs all workspace packages
pnpm db:generate              # generates the Prisma client
```

### 2. Start Required Databases

```bash
# Starts PostgreSQL 15, pgvector/pg17, Neo4j 5, and Redis 7
docker compose -f docker-compose.prod.yml up -d postgres pgvector neo4j redis
```

### 3. Start the Auth Service

```bash
pnpm dev:auth                 # Express + Better Auth on port 4000
```

### 4. Start the Frontend

```bash
pnpm dev                      # Next.js with Turbopack on port 3000
```

### 5. Start Python Services

```bash
# FastAPI ML engine
cd apps/api
pip install -r requirements.txt
uvicorn main:app --reload     # port 8000

# Face recognition service (separate terminal)
cd apps/deepface
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8001
```

### 6. Full Production Stack

For the complete 9-service stack (including Nginx, go2rtc, and all four application services):

```bash
bash scripts/deploy.sh
```

### 7. Access the Application

| Service | URL |
|---------|-----|
| Dashboard | [http://localhost:3000](http://localhost:3000) |
| Auth API | [http://localhost:4000](http://localhost:4000) |
| Backend API | [http://localhost:8000](http://localhost:8000) |
| API Docs (Swagger) | [http://localhost:8000/docs](http://localhost:8000/docs) |

---

## 📂 Project Structure

```
fazri-analyzer/                   # pnpm workspace root (Turborepo)
├── apps/
│   ├── web/                      # Next.js 16 dashboard & admin UI (port 3000)
│   │   └── src/
│   │       ├── app/
│   │       │   ├── (app)/
│   │       │   │   ├── dashboard/    # Entity tracking, alerts, cameras, chat,
│   │       │   │   │                 #   face-enrollment, anomalies, zones,
│   │       │   │   │                 #   webhooks, events, insights
│   │       │   │   └── admin/        # SUPER_ADMIN: users, orgs, sessions,
│   │       │   │                     #   analytics, onboarding
│   │       │   └── (landing)/        # Public landing page
│   │       ├── components/
│   │       ├── hooks/
│   │       ├── lib/
│   │       └── types/
│   ├── auth/                     # Express + Better Auth v1.5.4 (port 4000)
│   │   └── src/
│   │       ├── auth.ts           # Better Auth config (plugins, RBAC, JWT, SSO)
│   │       ├── permissions.ts    # Org + admin access-control statements & roles
│   │       └── index.ts          # Express server entry point
│   ├── api/                      # FastAPI ML engine (port 8000)
│   │   ├── routes/               # alert, anomaly, deepface, spatial, webhook,
│   │   │                         #   events, staff, notification, system routes
│   │   ├── services/             # alert, chatbot (Gemini), deepface batch sync,
│   │   │                         #   hikvision_poller, aruba_poller, webhooks
│   │   ├── connectors/           # hikvision_client, aruba_client
│   │   ├── models/db/            # SQLAlchemy models (alerts, cameras, webhooks,
│   │   │                         #   sensor events, entity profiles, push subs)
│   │   ├── simulators/           # Hikvision & Aruba device simulators
│   │   ├── config/               # Pydantic settings (all env vars)
│   │   ├── main.py               # FastAPI app + lifespan startup
│   │   └── requirements.txt
│   └── deepface/                 # InsightFace recognition service
│       └── app/
│           ├── face_engine.py    # InsightFace buffalo_l loader
│           ├── pgvector_service.py # Embedding upsert & HNSW search
│           ├── stream.py         # RTSP stream-based detection
│           └── routes.py
├── packages/
│   ├── db/                       # Shared Prisma schema & generated client
│   │   └── prisma/
│   │       └── schema.prisma     # user, session, account, organization,
│   │                             #   member, invitation, ssoProvider, jwks
│   └── config/                   # Shared ESLint & TypeScript configs
├── nginx/                        # nginx.conf — reverse proxy + SSL
├── mediamtx/                     # go2rtc Dockerfile + config
├── scripts/
│   └── deploy.sh                 # Production deployment helper
├── docs/                         # Architecture & runbook documentation
├── .gitlab-ci.yml                # GitLab CI/CD pipeline configuration
├── Jenkinsfile                   # Jenkins pipeline (path-based parallel builds)
├── docker-compose.prod.yml       # 9-service production stack
├── pnpm-workspace.yaml
└── turbo.json
```

---

## 👥 Team

Built with ❤️ by Team Fazri | RDP Datacenter | Rayzrsole.

---

## 📄 License

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

This project is licensed under the **MIT License** - see below for the full text.

```
MIT License

Copyright (c) 2025 Team Fazri | RDP Datacenter | Rayzrsole

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```
