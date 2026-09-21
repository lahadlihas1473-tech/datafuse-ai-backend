from fastapi import FastAPI

from app.api.demolition import router as demolition_router
from app.api.pipeline import router as pipeline_router
from app.api.threedbag import router as threedbag_router
from app.api.materials import router as materials_router
# from app.api.email import router as email_router
from app.api.material_estimation import router as material_estimation_router
from app.api.notices import router as notices_router
from app.api.addresses import router as addresses_router
from fastapi.middleware.cors import CORSMiddleware


app = FastAPI(
    title="Resource Paspoort + DataFuseAI + MCP",
    version="1.0.0"
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
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


# Email router
# app.include_router(email_router)

@app.get("/")
def root():
    return {
        "message": "Welcome to the project"
    }