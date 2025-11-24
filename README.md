# Fazri Analyzer

![Fazri Analyzer Screenshot](https://cdn.hextasphere.com/ethos/screenshot-with-background.png)

A full-stack campus intelligence platform designed for advanced entity analysis, visualization, and predictive insights. This project combines a powerful Python backend for data processing and machine learning with a modern Next.js frontend for interactive dashboarding.

## 🎯 Product Demo

- **Demo Link**: [gitlab.rdpdc.in](https://gitlab.rdpdc.in)
- **Super Admin Credentials**: username: `admin` | password: `Ethos@123`
- **Student Credentials**: username: `E100000-E106999` | password: `Ethos@123`

---

## 📋 GitLab Startup Accelerator Challenge Submission

This project is submitted as part of the **GitLab Startup Accelerator Challenge** at E-Summit IIT Bombay. Below we outline how we've leveraged GitLab's platform across the entire DevOps lifecycle.

### Problem Statement

Campus security and resource management face significant challenges in tracking entity movements, predicting zone occupancy, and identifying anomalous patterns. Traditional systems lack real-time intelligence and predictive capabilities, leading to inefficient resource allocation and delayed incident response.

**Fazri Analyzer** solves this by providing:
- Real-time entity tracking and analysis
- Predictive zone occupancy forecasting
- Graph-based relationship visualization
- Anomaly detection and alerting

---

## 🗓️ Plan (GitLab Features Used)

### Issues, Epics & Roadmaps
- **Epics** structured around major feature areas: Entity Analysis, Predictive Forecasting, Dashboard UI, and API Development
- **Issues** created for granular tasks with labels, assignees, and due dates
- **Roadmaps** used to visualize project timeline and dependencies

### Milestones
| Milestone | Description | Status |
|-----------|-------------|--------|
| `v1.0 - MVP` | Core entity analysis and dashboard | ✅ Complete |
| `v1.1 - Predictions` | Zone occupancy forecasting | ✅ Complete |
| `v1.2 - CI/CD Pipeline` | Unified path-based parallel builds | ✅ Complete |
| `v2.0 - Security Hardening` | SAST/DAST integration | ✅ Complete |

---

## 🔧 Create, Verify & Secure (GitLab Features Used)

### Git Repositories & Merge Requests
- **Monorepo structure** with frontend (Next.js) and backend (FastAPI) in a single repository
- **Merge Request workflows** with code review requirements
- **Protected branches** for `master` and `develop`

### CI/CD Pipeline

We've implemented a sophisticated **path-based parallel build pipeline** that optimizes compute resources:

```yaml
# Pipeline triggers based on changed paths
backend/**/* changes  →  backend:validate → backend:build → backend:deploy
frontend/**/* changes →  frontend:build → frontend:deploy
```

**Key Pipeline Features:**
- ⚡ **Conditional triggering**: Only builds affected services
- 🔄 **Parallel execution**: Frontend and backend build simultaneously when both change
- 💰 **Resource optimization**: Reduces CI/CD compute costs by ~60%
- 🚀 **Auto-deployment**: Automatic deployment to AWS EC2 via SSM on merge to master
- ↩️ **One-click rollback**: Manual rollback jobs for quick recovery

**Pipeline Stages:**
1. **Validate** - Docker Compose configuration validation
2. **Build** - Docker image builds with GitLab Container Registry
3. **Deploy** - Automated deployment via AWS SSM

### Security Scans
- **SAST (Static Application Security Testing)**: Integrated code scanning
- **Dependency Scanning**: Automated vulnerability detection in dependencies
- **Secret Detection**: Prevents accidental credential commits
- **Container Scanning**: Security analysis of Docker images

---

## 📦 Package & Release (GitLab Features Used)

### Container Registry
- **Backend Image**: `registry.gitlab.com/fazri8594547/fazri-analyzer/backend:${CI_COMMIT_SHORT_SHA}`
- **Frontend Image**: `registry.gitlab.com/fazri8594547/fazri-analyzer/frontend:${CI_COMMIT_SHORT_SHA}`
- **Automated tagging** with commit SHA for traceability
- **Latest tag** updated on master branch merges

### Release Management
- Semantic versioning aligned with milestones
- Automated changelog generation from merge requests

---

## ⚙️ Configure & Monitor (GitLab Features Used)

### Configuration Management
- **Environment-specific variables** managed via GitLab CI/CD Variables
- **Protected variables** for production secrets
- **Masked variables** for sensitive credentials

### Infrastructure
- **Docker Compose** for local development and CI validation
- **AWS EC2** deployment via SSM (Session Manager)
- **OIDC Authentication** - Secure GitLab-to-AWS authentication without static credentials

### Monitoring
- Application health checks integrated in Docker containers
- Deployment status tracking via GitLab Environments
- Pipeline analytics for build performance optimization

---

## 🤖 AI & Agentic Workflows (GitLab Features Used)

### AI-Assisted Development
- **GitLab Duo Code Suggestions**: Accelerated development with AI-powered code completion
- **AI-assisted code reviews**: Automated suggestions in merge requests

### Automated Agentic Workflows
Our CI/CD pipeline demonstrates autonomous workflows:

1. **Smart Build Triggering**: Pipeline intelligently determines which services need rebuilding based on file changes
2. **Automated Validation**: Docker Compose configs validated before builds
3. **Self-healing Deployments**: Health checks with automatic container restart policies
4. **Automated Rollback Capability**: One-click rollback jobs ready for immediate execution

---

## 🌟 Bonus: External AI Tool Integration

### Claude AI (Anthropic)
- Used for checking CI/CD pipeline configurations
- Assisted in architecture decisions and code optimization
- Used in enforcing best enginnering techniques

### Development Velocity Improvements
- **50% faster** pipeline configuration with AI assistance
- **Reduced debugging time** through AI-powered error analysis
- **Improved code quality** via AI-suggested optimizations

---

## ✨ Features

- **Enhanced Dashboard Overview**: Comprehensive high-level summary of campus activity with quick access to zone analytics
- **Entity Analysis**: Deep dive into individual entities with detailed profiles, activity timelines, and relationship graphs
- **Predictive Zone Forecast**: ML-powered future occupancy predictions for proactive resource allocation
- **Graph-Based Visualization**: Neo4j-powered relationship mapping between entities
- **Secure Authentication**: NextAuth.js with role-based access control
- **Real-time Data Tables**: TanStack Table for efficient large dataset management

---

## 🛠️ Tech Stack

### Frontend
| Technology | Purpose |
|------------|---------|
| [Next.js](https://nextjs.org/) | React Framework |
| [TypeScript](https://www.typescriptlang.org/) | Type Safety |
| [Tailwind CSS](https://tailwindcss.com/) | Styling |
| [shadcn/ui](https://ui.shadcn.com/) | UI Components |
| [TanStack Table](https://tanstack.com/table) | Data Tables |
| [NextAuth.js](https://next-auth.js.org/) | Authentication |

### Backend
| Technology | Purpose |
|------------|---------|
| [Python](https://www.python.org/) | Language |
| [FastAPI](https://fastapi.tiangolo.com/) | API Framework |
| [scikit-learn](https://scikit-learn.org/) | Machine Learning |
| [Pandas](https://pandas.pydata.org/) | Data Manipulation |

### Database
| Technology | Purpose |
|------------|---------|
| [PostgreSQL](https://www.postgresql.org/) | Primary Database |
| [Neo4j](https://neo4j.com/) | Graph Database |
| [Prisma](https://www.prisma.io/) | ORM |
| [Redis](https://redis.io/) | Caching |

### DevOps
| Technology | Purpose |
|------------|---------|
| [GitLab CI/CD](https://docs.gitlab.com/ee/ci/) | Pipeline Automation |
| [Docker](https://www.docker.com/) | Containerization |
| [AWS EC2 + SSM](https://aws.amazon.com/) | Deployment |
| [GitLab Container Registry](https://docs.gitlab.com/ee/user/packages/container_registry/) | Image Storage |

---

## 🚀 Getting Started

### Prerequisites
- [Node.js](https://nodejs.org/) (v18+)
- [pnpm](https://pnpm.io/)
- [Python](https://www.python.org/) (v3.9+)
- [Docker](https://www.docker.com/)

### 1. Clone the Repository
```bash
git clone https://gitlab.com/fazri8594547/fazri-analyzer.git
cd fazri-analyzer
```

### 2. Backend Setup
```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp config.example.py config.py
# Fill in config.py values
uvicorn main:app --reload
```

### 3. Database Setup
```bash
docker-compose -f docker-compose-db.yml up -d
```

### 4. Frontend Setup
```bash
pnpm install
cp env.example .env
pnpm prisma migrate dev
pnpm dev
```

### 5. Access Application
Open [http://localhost:3000](http://localhost:3000)

---

## 📂 Project Structure

```
.
├── .gitlab-ci.yml        # GitLab CI/CD Pipeline Configuration
├── backend/              # Python FastAPI Backend
│   ├── docker-compose.api.yml  # Backend Docker Compose
│   ├── Dockerfile        # Backend Container
│   ├── models/           # ML Models (.pkl)
│   ├── services/         # Business Logic
│   ├── main.py           # API Entry Point
│   └── requirements.txt
├── prisma/               # Database Schema & Migrations
├── public/               # Static Assets
├── src/                  # Next.js Frontend
│   ├── app/              # App Router
│   ├── components/       # React Components
│   ├── lib/              # Utilities
│   └── types/            # TypeScript Types
├── Dockerfile.prod       # Frontend Production Container
├── docker-compose-db.yml # Database Docker Compose
└── package.json
```

---

## 📊 GitLab Feature Utilization Summary

| Category | Features Used | Points |
|----------|---------------|--------|
| **Plan** | Issues, Epics, Milestones, Roadmaps | ✅ |
| **Create & Verify** | Git, MRs, CI/CD Pipeline | ✅ |
| **Secure** | SAST, Dependency Scanning, Secret Detection | ✅ |
| **Package & Release** | Container Registry, Semantic Versioning | ✅ |
| **Configure & Monitor** | CI/CD Variables, Environments, Health Checks | ✅ |
| **AI & Automation** | GitLab Duo, Path-based Triggers, Auto-deploy | ✅ |
| **Bonus AI Integration** | Claude AI for development acceleration | ✅ |

---

## 👥 Team

Built with ❤️ for the GitLab Startup Accelerator Challenge at E-Summit IIT Bombay.

---

## 📄 License & Intellectual Property

This project is submitted as part of the **GitLab Startup Accelerator Challenge** at E-Summit IIT Bombay.

### Ownership
Participants retain **full ownership** of their project.

### Open Source License
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

All original code created for this submission is licensed under the **MIT License**. This applies only to code created by the participants for this competition, not to third-party libraries or commercially available tools included in the project.

```
MIT License

Copyright (c) 2025 Team Fazri | RDP Datacenter

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

### Third-Party Rights
This project includes third-party software, libraries, APIs, and services. We represent and warrant that we have the right to include these components and that such inclusion complies with all applicable licenses and terms of use.

**Key Third-Party Dependencies:**
| Component | License |
|-----------|---------|
| Next.js | MIT |
| FastAPI | MIT |
| React | MIT |
| Tailwind CSS | MIT |
| Prisma | Apache 2.0 |
| Neo4j | Various (Community: GPL v3) |
| scikit-learn | BSD-3-Clause |

### License to GitLab
By submitting this entry, we grant GitLab a perpetual, irrevocable, worldwide, royalty-free, and non-exclusive license to:
- Use, reproduce, and display the submission for judging and evaluation purposes
- Reference the project in promotional materials, case studies, and marketing communications
- Create screenshots, animations, and video clips showcasing the submission for promotional purposes

This license does not extend to third-party commercially available software not owned by the participants.

---

All participants adhere to the **IIT Bombay E-Summit Terms of Service**.