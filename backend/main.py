# backend/app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import entity_routes, graph_routes, spatial_routes, anomaly_routes, chat_routes

app = FastAPI(
    title="Campus Entity Resolution API",
    description="API for campus security monitoring and entity tracking",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(entity_routes.router)
app.include_router(graph_routes.router)
app.include_router(spatial_routes.router)
app.include_router(anomaly_routes.router)
app.include_router(chat_routes.router)

@app.get("/")
async def root():
    return {
        "message": "Campus Entity Resolution API",
        "status": "running",
        "version": "1.0.0"
    }

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)