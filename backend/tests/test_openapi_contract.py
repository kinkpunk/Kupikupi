from pathlib import Path

import yaml

from app.main import create_app


def test_openapi_draft_paths_match_backend_schema() -> None:
    draft = _load_openapi_draft()
    generated = create_app().openapi()

    draft_paths = _path_methods(draft, prefix="")
    generated_paths = _path_methods(generated, prefix="/v1")

    assert draft_paths == generated_paths


def test_openapi_draft_local_refs_resolve() -> None:
    draft = _load_openapi_draft()
    refs = list(_iter_local_refs(draft))

    assert refs
    for ref in refs:
        assert _resolve_json_pointer(draft, ref) is not None, f"Unresolved OpenAPI ref: {ref}"


def _load_openapi_draft() -> dict[str, object]:
    repository_root = Path(__file__).resolve().parents[2]
    draft = yaml.safe_load((repository_root / "packages/openapi/openapi.yaml").read_text())
    assert isinstance(draft, dict)
    return draft


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


def _iter_local_refs(value: object):
    if isinstance(value, dict):
        ref = value.get("$ref")
        if isinstance(ref, str) and ref.startswith("#/"):
            yield ref
        for item in value.values():
            yield from _iter_local_refs(item)
    elif isinstance(value, list):
        for item in value:
            yield from _iter_local_refs(item)


def _resolve_json_pointer(document: dict[str, object], pointer: str) -> object | None:
    current: object = document
    for raw_part in pointer.removeprefix("#/").split("/"):
        part = raw_part.replace("~1", "/").replace("~0", "~")
        if not isinstance(current, dict) or part not in current:
            return None
        current = current[part]
    return current
