"""Local read-only HTTP adapter. All domain work belongs to Dataset."""

from pathlib import Path
import json

from fastapi import Body, FastAPI, Query, Request
from fastapi.responses import FileResponse, JSONResponse

from .dataset import Dataset, DatasetError


def create_app(dataset: Dataset, ui_dist: str | Path | None = None) -> FastAPI:
    app = FastAPI(title="GTNH Data", version="0.1.0")

    def structured(operation, arguments):
        try:
            return getattr(dataset, operation)(**arguments)
        except TypeError as error:
            raise DatasetError(str(error)) from error

    @app.exception_handler(DatasetError)
    async def domain_error(request: Request, error: DatasetError):
        message = str(error)
        status = 409 if "replaced" in message else 404 if message.startswith("Unknown ") else 400
        return JSONResponse({"error": message}, status_code=status)

    @app.get("/api/status")
    def status():
        return dataset.status()

    @app.get('/api/flow-index')
    def flow_index():
        return dataset.flow_index_status()

    @app.post('/api/flow-index/rebuild')
    def rebuild_flow_index():
        return dataset.rebuild_flow_index()

    @app.get("/api/resources")
    def resources(q: str = "", kind: str | None = None, offset: int = 0, limit: int = 50, profile_id: str | None = None, scope: str | None = None):
        try:
            decoded_scope = None if scope is None else json.loads(scope)
        except json.JSONDecodeError as error:
            raise DatasetError('scope must be a JSON object') from error
        return dataset.find_resources(q=q, kind=kind, offset=offset, limit=limit, profile_id=profile_id, scope=decoded_scope)

    @app.get('/api/resource-groups')
    def resource_groups(q: str = '', offset: int = 0, limit: int = 20):
        return dataset.find_resource_groups(q=q, offset=offset, limit=limit)

    @app.get('/api/scope-catalog')
    def scope_catalog():
        return dataset.get_scope_catalog()

    @app.get('/api/boundary-profiles')
    def boundary_profiles():
        return dataset.list_boundary_profiles()

    @app.get('/api/boundary-profiles/{profile_id}')
    def boundary_profile(profile_id: str):
        return dataset.get_boundary_profile(profile_id)

    @app.post('/api/boundary-profiles/{profile_id}')
    def save_boundary_profile(profile_id: str, arguments: dict = Body(...)):
        return structured('save_boundary_profile', dict(arguments, profile_id=profile_id))

    @app.delete('/api/boundary-profiles/{profile_id}')
    def delete_boundary_profile(profile_id: str, arguments: dict = Body(default={})):
        return structured('delete_boundary_profile', dict(arguments, profile_id=profile_id))

    @app.post('/api/plan-to-bases')
    def plan_to_bases(arguments: dict = Body(...)):
        return structured('plan_to_bases', arguments)

    @app.post('/api/energy-audit')
    def energy_audit(arguments: dict = Body(...)):
        return structured('audit_energy', arguments)

    @app.post('/api/statistics')
    def statistics(arguments: dict = Body(default={})):
        return structured('analyze_statistics', arguments)

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

    @app.get("/api/sources/{id:path}")
    def source(id: str):
        return dataset.get_source(id)

    @app.get("/api/environments")
    def environments(q: str = "", offset: int = 0, limit: int = 50):
        return dataset.find_environments(q=q, offset=offset, limit=limit)

    @app.get("/api/trace")
    def trace(start_id: str, target_id: str, max_depth: int = 12, max_processes: int = 300, max_paths: int = 8,
              max_extra_steps: int = 6, path_selection: str = 'diverse', required_resource_id: list[str] = Query(default=[]), excluded_resource_id: list[str] = Query(default=[]),
              excluded_group_id: list[str] = Query(default=[]),
              min_tier: int | None = None, max_tier: int | None = None, unknown_tier_policy: str = 'exclude', view: str = 'full',
              terminal_artifact_policy: str = Query(default='allow', description='direct_targets_only retains direct tool and part targets and required cofeeds, but blocks recognized tools and parts on paths to ordinary outputs. Recognition uses captured runtime class ancestry. Inspect search.terminal_artifacts for recognition limits.')):
        return dataset.trace_processes(start_id=start_id, target_id=target_id, max_depth=max_depth, max_processes=max_processes,
                                       max_paths=max_paths, max_extra_steps=max_extra_steps, path_selection=path_selection,
                                       required_resource_ids=required_resource_id, excluded_resource_ids=excluded_resource_id,
                                       excluded_group_ids=excluded_group_id,
                                       min_tier=min_tier, max_tier=max_tier, unknown_tier_policy=unknown_tier_policy, view=view,
                                       terminal_artifact_policy=terminal_artifact_policy)

    @app.post('/api/recycling-plan')
    def recycling_plan(arguments: dict = Body(...)):
        return structured('plan_recycling', arguments)

    @app.get('/api/chemistry/{resource_id:path}')
    def chemistry(resource_id: str):
        return dataset.inspect_chemistry(resource_id=resource_id)

    @app.get('/api/acquisition/{resource_id:path}')
    def acquisition(resource_id: str, profile_id: str | None = None, max_depth: int = 8, max_processes: int = 200, max_variants: int = 128, max_resources: int = 512):
        return dataset.inspect_acquisition(resource_id=resource_id, profile_id=profile_id, max_depth=max_depth, max_processes=max_processes, max_variants=max_variants, max_resources=max_resources)

    @app.get('/api/loops')
    def loops(start_id: str, kind: str = 'any', chemical_kind: str = 'any', yield_mode: str = 'guaranteed', max_depth: int = Query(default=6, ge=1, le=20),
              max_processes: int = Query(default=200, ge=1, le=1000), max_paths: int = 20, max_states: int = Query(default=5000, ge=1, le=50000),
              min_tier: int | None = None, max_tier: int | None = None, unknown_tier_policy: str = 'exclude'):
        return dataset.find_loops(start_id=start_id, kind=kind, chemical_kind=chemical_kind, yield_mode=yield_mode, max_depth=max_depth,
                                  max_processes=max_processes, max_paths=max_paths, max_states=max_states,
                                  min_tier=min_tier, max_tier=max_tier, unknown_tier_policy=unknown_tier_policy)

    @app.post('/api/loops')
    def selected_loops(arguments: dict = Body(...)):
        return structured('find_loops', arguments)

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
