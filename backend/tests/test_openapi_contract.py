from pathlib import Path

import yaml

from app.main import create_app


def test_openapi_draft_paths_match_backend_schema() -> None:
    repository_root = Path(__file__).resolve().parents[2]
    draft = yaml.safe_load((repository_root / "packages/openapi/openapi.yaml").read_text())
    generated = create_app().openapi()

    draft_paths = _path_methods(draft, prefix="")
    generated_paths = _path_methods(generated, prefix="/v1")

    assert draft_paths == generated_paths


def _path_methods(schema: dict[str, object], *, prefix: str) -> dict[str, set[str]]:
    paths = schema.get("paths", {})
    assert isinstance(paths, dict)
    normalized = {}
    for path, operations in paths.items():
        assert isinstance(path, str)
        assert isinstance(operations, dict)
        normalized_path = path.removeprefix(prefix)
        normalized[normalized_path] = {
            method
            for method in operations
            if method in {"get", "post", "put", "patch", "delete"}
        }
    return normalized
