from fastapi import FastAPI

from app.api.demolition import router as demolition_router
from app.api.pipeline import router as pipeline_router
from app.api.threedbag import router as threedbag_router
from app.api.materials import router as materials_router
# from app.api.email import router as email_router
from app.api.material_estimation import router as material_estimation_router
from app.api.notices import router as notices_router
from app.api.addresses import router as addresses_router
from app.api.method_2 import router as method_2_router
from fastapi.middleware.cors import CORSMiddleware


app = FastAPI(
    title="Resource Paspoort + DataFuseAI + MCP",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "*",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Existing demolition endpoints
app.include_router(demolition_router)

# Pipeline endpoints
app.include_router(pipeline_router)

app.include_router(threedbag_router)
app.include_router(materials_router)
app.include_router(material_estimation_router)
app.include_router(notices_router)
app.include_router(addresses_router)

# Method 2: geometry-based material and CO2 estimate (public.method_2)
app.include_router(method_2_router)


# Email router
# app.include_router(email_router)


@app.get("/")
def root():
    return {
        "message": "Welcome to the project"
    }