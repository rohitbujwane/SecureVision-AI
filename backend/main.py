"""
FastAPI application entry point.
Configures CORS, mounts static files, initializes database and model.
"""

import sys
from pathlib import Path

# Ensure project root is on the path
project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from backend.config import APP_NAME, APP_VERSION, CORS_ORIGINS, FRONTEND_DIR
from backend.database import init_db
from backend.routes.api import router
from backend.services.detector import detector


app = FastAPI(
    title=APP_NAME,
    version=APP_VERSION,
    description="AI-Based Security Log Analyzer and Explainable Anomaly Detection System",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(router)

# Mount frontend static files
if FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")


@app.on_event("startup")
def startup():
    """Initialize database and load model on startup."""
    init_db()
    # Try to load existing model
    if detector.load():
        print(f"[INFO] Model loaded: {detector.version} with {len(detector.features)} features")
    else:
        print("[INFO] No trained model found. Upload a dataset to train automatically.")


@app.get("/", include_in_schema=False)
async def serve_frontend():
    """Serve the frontend dashboard."""
    index_path = FRONTEND_DIR / "index.html"
    if index_path.exists():
        return FileResponse(str(index_path))
    return {"message": "Frontend not found. Access API docs at /docs"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="127.0.0.1", port=8000, reload=True)
