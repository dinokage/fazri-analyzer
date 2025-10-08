# Fazri Analyzer

A full-stack application designed for advanced entity analysis, visualization, and predictive insights. This project combines a powerful Python backend for data processing and machine learning with a modern Next.js frontend for interactive dashboarding.

## Product Demo

- Demo Link: [ethos.rdpdc.in]('https://ethos.rdpdc.in')
- Super Admin Credentials: username-`admin` password-`Ethos@123`
- Student Credentials: username-`<entity-id>` password-`Ethos@123`

## ✨ Features

- **Interactive Dashboard**: A responsive and intuitive user interface built with Next.js, shadcn/ui, and Tailwind CSS.
- **Entity Analysis**: Deep dive into individual entities with detailed profiles, activity timelines, and relationship graphs.
- **Predictive Insights**: Leverage machine learning models to generate predictions and confidence scores for entity behavior.
- **Graph-Based Visualization**: Understand complex relationships between entities through graph-based data modeling.
- **Secure Authentication**: User authentication and session management handled by NextAuth.js.
- **TanStack Table**: Efficiently display and manage large datasets of entities.

## 🛠️ Tech Stack

### Frontend

- **Framework**: [Next.js](https://nextjs.org/) (React)
- **Language**: [TypeScript](https://www.typescriptlang.org/)
- **Styling**: [Tailwind CSS](https://tailwindcss.com/)
- **UI Components**: [shadcn/ui](https://ui.shadcn.com/)
- **State Management/Data Fetching**: SWR/React Query (inferred from TanStack Table usage)
- **Tables**: [TanStack Table](https.tanstack.com/table)
- **Authentication**: [NextAuth.js](https://next-auth.js.org/)

### Backend

- **Language**: [Python](https://www.python.org/)
- **Framework**: FastAPI (assumed from file structure)
- **Machine Learning**: scikit-learn (inferred from `.pkl` models)
- **Data Manipulation**: Pandas
- **Database/Graph**: Neo4j/Graph Database (inferred from graph-related files)

### Database

- **ORM**: [Prisma](https://www.prisma.io/)
- **Database**: PostgreSQL (inferred from `docker-compose-db.yml` and common Prisma usage)
- **Graph Database**: Neo4j

### DevOps

- **Package Manager**: [pnpm](https://pnpm.io/)
- **Containerization**: [Docker](https://www.docker.com/)
- **CI/CD**: [Vercel]('https://vercel.com') for frontend, [RDP Datacenter]('https://rdpdatacenter.in') for backend

## 🚀 Getting Started

Follow these instructions to get a local copy of the project up and running.

### Prerequisites

- [Node.js](https://nodejs.org/en/) (v18 or newer)
- [pnpm](https://pnpm.io/installation)
- [Python](https://www.python.org/downloads/) (v3.9 or newer)
- [Docker](https://www.docker.com/products/docker-desktop/)

### 1. Clone the Repository

```bash
git clone https://github.com/dinokage/fazri-analyzer
cd fazri-analyzer
```

### 2. Backend Setup

```bash
# Navigate to the backend directory
cd backend

# Create and activate a virtual environment
python -m venv venv
source venv/bin/activate  # On Windows, use `venv\Scripts\activate`

# Install Python dependencies
pip install -r requirements.txt

# Set up environment variables (create config.py from config.example.py)
cp config.example.py config.py
# ...fill in the necessary values in config.py

# Run the backend server
# (Command may vary based on the actual framework used, e.g., uvicorn)
uvicorn main:app --reload
```

### 3. Database Setup

```bash
# In the root directory, start the PostgreSQL database using Docker
docker-compose -f docker-compose-db.yml up -d
```

### 4. Frontend Setup

```bash
# Navigate to the root directory
cd ..

# Install frontend dependencies
pnpm install

# Create a .env.local file for environment variables
cp env.example .env

# Apply database migrations
pnpm prisma migrate dev

# Run the frontend development server
pnpm dev
```

### 5. Access the Application

Open your browser and navigate to `http://localhost:3000`.

## 📂 Project Structure

```

.
├── backend/         # Python backend (FastAPI/Flask)
│   ├── models/      # Trained ML models (.pkl)
│   ├── services/    # Business logic (entity resolution, ML prediction)
│   ├── main.py      # API entry point
│   └── requirements.txt
├── prisma/          # Prisma schema and migrations
│   └── schema.prisma
├── public/          # Static assets for the frontend
├── src/             # Next.js frontend application
│   ├── app/         # App Router: pages, layouts, and API routes
│   ├── components/  # Reusable React components
│   ├── lib/         # Helper functions and utilities
│   └── types/       # TypeScript type definitions
├── docker-compose-db.yml # Docker configuration for the database
├── next.config.ts   # Next.js configuration
└── package.json     # Frontend dependencies and scripts

```
