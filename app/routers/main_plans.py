from fastapi import FastAPI

from app.core.database import Base, engine
from app.routers import plans

app = FastAPI(
    title="SubFlow API",
    version="1.0.0"
)

# Register Plans Router
app.include_router(plans.router)

# Create database tables
Base.metadata.create_all(bind=engine)


@app.get("/")
def home():
    return {
        "message": "Welcome to SubFlow API"
    }