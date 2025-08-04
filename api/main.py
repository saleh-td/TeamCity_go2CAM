from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from .routes import builds, agents
import os
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)

app = FastAPI(
    title="TeamCity Monitor API",
    description="API pour le monitoring des builds TeamCity",
    version="1.0.0"
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Routes principales pour le frontend existant
app.include_router(builds.router, prefix="/api", tags=["builds"])
app.include_router(agents.router, prefix="/api", tags=["agents"])
# Plus de configurations.router - intégré dans builds.router

frontend_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend")
app.mount("/static", StaticFiles(directory=frontend_path), name="static")

@app.get("/")
async def root():
    return {
        "message": "Bienvenue sur l'API TeamCity Monitor",
        "version": "1.0.0",
        "documentation": "/docs",
        "dashboard": "/static/index.html",
        "endpoints": {
            "builds": "/api/builds",
            "agents": "/api/agents", 
            "config": "/api/config",
            "dashboard": "/api/builds/dashboard",
            "tree": "/api/builds/tree",
            "selection": "/api/builds/tree/selection"
        }
    } 