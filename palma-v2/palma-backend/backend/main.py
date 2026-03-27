from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import sys
import os

# Add the current directory to sys.path so we can import 'routers' directly
# This fixes the issue on Render where the working directory is the parent folder
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from routers.predict import router as predict_router

app = FastAPI(
    title="PalmaCount Backend API",
    description="FastAPI backend for PalmaCount - YOLOv8 oil palm classification",
    version="1.0"
)

# CORS middleware to allow frontend requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For development, allow all origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include the predict router
app.include_router(predict_router, prefix="/api")

# Simple test endpoint
@app.get("/")
def home():
    return {"message": "PalmaCount FastAPI Backend is running!"}
