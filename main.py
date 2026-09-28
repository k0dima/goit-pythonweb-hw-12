from src.api import contacts, users, auth
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import redis.asyncio as redis


from src.conf.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.redis = redis.from_url(
        settings.REDIS_URL,
        decode_responses=True,
    )
    try:
        yield
    finally:
        await app.state.redis.aclose()


app = FastAPI(lifespan=lifespan)
origins = ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api", tags=["auth"])
app.include_router(contacts.router, prefix="/api", tags=["contacts"])
app.include_router(users.router, prefix="/api", tags=["users"])

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
