"""Local read-only HTTP adapter. All domain work belongs to Dataset."""

from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse

from .dataset import Dataset, DatasetError


def create_app(dataset: Dataset, ui_dist: str | Path | None = None) -> FastAPI:
    app = FastAPI(title="GTNH Data", version="0.1.0")

    @app.exception_handler(DatasetError)
    async def domain_error(request: Request, error: DatasetError):
        message = str(error)
        status = 409 if "replaced" in message else 404 if message.startswith("Unknown ") else 400
        return JSONResponse({"error": message}, status_code=status)

    @app.get("/api/status")
    def status():
        return dataset.status()

    @app.get("/api/resources")
    def resources(q: str = "", kind: str | None = None, offset: int = 0, limit: int = 50):
        return dataset.find_resources(q=q, kind=kind, offset=offset, limit=limit)

    @app.get("/api/resources/{id:path}")
    def resource(id: str):
        return dataset.get_resource(id)

    @app.get("/api/processes")
    def processes(input_id: str | None = None, output_id: str | None = None, family: str | None = None, offset: int = 0, limit: int = 50):
        return dataset.find_processes(input_id=input_id, output_id=output_id, family=family, offset=offset, limit=limit)

    @app.get("/api/processes/{id:path}")
    def process(id: str):
        return dataset.get_process(id)

    @app.get("/api/groups/{id:path}")
    def group(id: str):
        return dataset.get_group(id)

    @app.get("/api/sources")
    def sources(resource_id: str | None = None, environment_id: str | None = None, offset: int = 0, limit: int = 50):
        return dataset.find_sources(resource_id=resource_id, environment_id=environment_id, offset=offset, limit=limit)

    @app.get("/api/environments")
    def environments(q: str = "", offset: int = 0, limit: int = 50):
        return dataset.find_environments(q=q, offset=offset, limit=limit)

    @app.get("/api/trace")
    def trace(start_id: str, target_id: str, max_depth: int = 12, max_processes: int = 300):
        return dataset.trace_processes(start_id=start_id, target_id=target_id, max_depth=max_depth, max_processes=max_processes)

    if ui_dist is not None:
        directory = Path(ui_dist).resolve()
        if not (directory / "index.html").is_file():
            raise DatasetError(f"Built UI not found at {directory}. Build ui or pass --ui-dist")

        @app.get("/{path:path}", include_in_schema=False)
        def ui(path: str):
            if path == "api" or path.startswith("api/"):
                return JSONResponse({"error": "Unknown API route"}, status_code=404)
            file = (directory / path).resolve()
            if not file.is_relative_to(directory):
                return JSONResponse({"error": "Invalid asset path"}, status_code=404)
            return FileResponse(file if file.is_file() else directory / "index.html")

    return app
