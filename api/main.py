from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from .routes import builds, agents, configurations
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


app.include_router(builds.router, prefix="/api/v1", tags=["builds"])
app.include_router(agents.router)
app.include_router(configurations.router, prefix="/api", tags=["configurations"])

app.include_router(builds.router, prefix="/api", tags=["builds-legacy"])

frontend_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend")
app.mount("/static", StaticFiles(directory=frontend_path), name="static")

@app.get("/")
async def root():
    return {
        "message": "Bienvenue sur l'API TeamCity Monitor",
        "version": "1.0.0",
        "documentation": "/docs",
        "dashboard": "/static/index.html"
    } 