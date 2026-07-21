from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .config import get_settings
from .routers import admin,tenant,public,webhooks
app=FastAPI(title="BarberFlow API",version="1.0.0",description="API multiempresa; tenant derivado do JWT.")
app.add_middleware(CORSMiddleware,allow_origins=get_settings().cors_origins.split(","),allow_credentials=True,allow_methods=["GET","POST","PATCH","DELETE"],allow_headers=["Authorization","Content-Type","X-Evolution-Signature"])
app.include_router(admin.router)
app.include_router(tenant.router)
app.include_router(public.router)
app.include_router(webhooks.router)
@app.get("/health",tags=["operation"])
async def health(): return {"status":"ok"}
