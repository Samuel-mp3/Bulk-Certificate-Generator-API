from fastapi import FastAPI

from app.database import Base, engine
from app.routers import certificates, jobs

# Create DB tables automatically on startup
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Bulk Certificate Generator API",
    description="Backend API for asynchronous bulk PDF certificate generation with status tracking.",
    version="1.0.0",
)

# Register endpoint routers
app.include_router(jobs.router)
app.include_router(certificates.router)


@app.get("/health", tags=["Health"])
def health_check():
    """Health check endpoint returning system status."""
    return {"status": "ok"}
