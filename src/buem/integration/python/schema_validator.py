import argparse
import json
from pathlib import Path
from typing import Any, cast

from jsonschema import Draft202012Validator, ValidationError


def _integration_dir() -> Path:
    return Path(__file__).resolve().parents[1]


def _parse_version_dir_name(name: str) -> tuple[int, ...] | None:
    if not name.startswith("v"):
        return None
    raw = name[1:].replace("_", ".")
    parts = raw.split(".")
    if not parts or any(p == "" for p in parts):
        return None
    try:
        return tuple(int(p) for p in parts)
    except ValueError:
        return None


def _latest_version_dir(schemas_dir: Path) -> str:
    if not schemas_dir.exists():
        raise FileNotFoundError(f"Schemas directory not found: {schemas_dir}")

    candidates: list[tuple[tuple[int, ...], str]] = []
    for child in schemas_dir.iterdir():
        if child.is_dir():
            parsed = _parse_version_dir_name(child.name)
            if parsed is not None:
                candidates.append((parsed, child.name))

    if not candidates:
        raise FileNotFoundError(f"No versioned schema directories found under: {schemas_dir}")

    candidates.sort(key=lambda x: x[0])
    return candidates[-1][1]


def _default_paths(version: str) -> dict[str, Path]:
    base = _integration_dir() / "schemas" / version
    return {
        "request_schema": base / "request_schema.json",
        "response_schema": base / "response_schema.json",
        "request_instance": base / "example_request.json",
        "response_instance": base / "example_response.json",
    }


def _load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as e:
        raise FileNotFoundError(f"File not found: {path}") from e
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in {path}: {e}") from e


def _validate_payload(*, label: str, schema_path: Path, instance_path: Path | None, instance_data: dict[str, Any] | None) -> int:
    schema = cast(Any, _load_json(schema_path))

    if instance_data is not None:
        instance = instance_data
        src = "provided payload"
    elif instance_path is not None:
        instance = _load_json(instance_path)
        src = str(instance_path)
    else:
        raise ValueError("Either instance_path or instance_data must be provided")

    try:
        Draft202012Validator.check_schema(schema)
        Draft202012Validator(schema).validate(instance)
        print(f"VALID {label}: {src} matches {schema_path}")
        return 0
    except (ValidationError, ValueError, FileNotFoundError) as e:
        print(f"INVALID {label}: {src} does not match {schema_path}")
        print(e)
        return 2


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Validate BUEM request/response payloads against versioned JSON Schemas")
    p.add_argument("--version", default=None, help="Schema version dir (e.g. v2). Default: latest under schemas/")
    p.add_argument("--kind", choices=["request", "response", "both"], default="both")
    p.add_argument("--request-schema", type=Path, default=None)
    p.add_argument("--request-instance", type=Path, default=None)
    p.add_argument("--response-schema", type=Path, default=None)
    p.add_argument("--response-instance", type=Path, default=None)

    args = p.parse_args(argv)

    schemas_dir = _integration_dir() / "schemas"
    version = args.version or _latest_version_dir(schemas_dir)
    defaults = _default_paths(version)

    request_schema = (args.request_schema or defaults["request_schema"]).resolve()
    request_instance = (args.request_instance or defaults["request_instance"]).resolve()
    response_schema = (args.response_schema or defaults["response_schema"]).resolve()
    response_instance = (args.response_instance or defaults["response_instance"]).resolve()

    codes: list[int] = []
    if args.kind in {"request", "both"}:
        codes.append(_validate_payload(label="request", schema_path=request_schema, instance_path=request_instance, instance_data=None))
    if args.kind in {"response", "both"}:
        codes.append(_validate_payload(label="response", schema_path=response_schema, instance_path=response_instance, instance_data=None))

    return 0 if all(c == 0 for c in codes) else 2


if __name__ == "__main__":
    raise SystemExit(main())