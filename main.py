from dotenv import load_dotenv

# Load environment variables FIRST, before any other imports
load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from routers import health, outbound_twillio, eval_api, transcript_ui
import uvicorn


def create_app() -> FastAPI:
    app = FastAPI(title="VakLab AI Agents")
    
    # Add CORS for UI access
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Mount static files for the transcript UI
    app.mount("/static", StaticFiles(directory="frontend"), name="static")
    
    # Include routers
    app.include_router(health.router)
    app.include_router(outbound_twillio.router)
    app.include_router(eval_api.router)
    app.include_router(transcript_ui.router)

    return app


app = create_app()

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)