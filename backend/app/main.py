from fastapi import FastAPI

from app.routers.agent import router as agent_router
from app.routers.customer_router import router as customer_router
from app.routers.health import router as health_router

app = FastAPI(title="Followup Voice Agent Backend")
app.include_router(health_router)
app.include_router(customer_router)
app.include_router(agent_router)
