from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from pm_bot.config import AppConfig
from pm_bot.storage.db import connect_database, initialize_database, require_supported_versions
from pm_bot.storage.repositories import ProjectionRepository

TEMPLATES = Jinja2Templates(directory=str(Path(__file__).with_name("templates")))


def create_app(config: AppConfig) -> FastAPI:
    app = FastAPI(title="Polymarket Bot V3 Dashboard")

    @app.get("/", response_class=HTMLResponse)
    def dashboard(request: Request) -> HTMLResponse:
        connection = connect_database(config.database_path)
        initialize_database(connection)
        require_supported_versions(connection)
        repository = ProjectionRepository(connection)
        snapshot = repository.fetch_dashboard_snapshot()
        positions = repository.fetch_open_positions()
        latest_session = repository.fetch_latest_session_state()
        return TEMPLATES.TemplateResponse(
            request=request,
            name="dashboard.html",
            context={
                "snapshot": snapshot,
                "positions": positions,
                "latest_session": latest_session,
            },
        )

    return app
