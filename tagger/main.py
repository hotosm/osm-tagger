from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from tagger.api.v1 import tags

app = FastAPI(
    title="My FastAPI App", description="A basic FastAPI application", version="1.0.0"
)

origins = [
    "*",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(tags.router, prefix="/api/v1")


@app.get("/api/health")
async def health():
    return {"status": "ok"}
