from fastapi import FastAPI

from tagger.api.v1 import tags

app = FastAPI(
    title="My FastAPI App", description="A basic FastAPI application", version="1.0.0"
)

# Include routers
app.include_router(tags.router, prefix="/api/v1")


@app.get("/api/health")
async def health():
    return {"status": "ok"}
