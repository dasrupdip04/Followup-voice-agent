from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers.agent import router as agent_router
from app.routers.customer_router import router as customer_router
from app.routers.health import router as health_router

app = FastAPI(title="Followup Voice Agent Backend")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:5174",
    ],
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)
app.include_router(health_router)
app.include_router(customer_router)
app.include_router(agent_router)
