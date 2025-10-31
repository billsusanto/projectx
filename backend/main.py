from dotenv import load_dotenv
load_dotenv()

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import init_db
from app.utils.logger import logger
from app.routes.todos import router as todos_router
from app.routes.chatbot import router as chatbot_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    logger.info("Database initialized")
    yield

app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

logger.instrument_fastapi(app)

app.include_router(todos_router)
app.include_router(chatbot_router)

@app.get("/health")
def read_root():
    return {"status": "ok"}