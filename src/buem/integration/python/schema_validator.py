import argparse
import json
from pathlib import Path
from typing import Any, cast

from jsonschema import ValidationError, validate, Draft202012Validator


def _integration_dir() -> Path:
    # This file lives in: integration/python/schema_validator.py
    return Path(__file__).resolve().parents[1]


def _parse_version_dir_name(name: str) -> tuple[int, ...] | None:
    # Accept v1, v2, v10, v2_1, v2.1.3 etc and compare numerically.
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
        if not child.is_dir():
            continue
        parsed = _parse_version_dir_name(child.name)
        if parsed is None:
            continue
        candidates.append((parsed, child.name))

    if not candidates:
        raise FileNotFoundError(f"No versioned schema directories found under: {schemas_dir}")

    candidates.sort(key=lambda x: x[0])
    return candidates[-1][1]


def _default_paths(version: str) -> dict[str, Path]:
    integration_dir = _integration_dir()
    return {
        "request_schema": integration_dir / "schemas" / version / "request_schema.json",
        "response_schema": integration_dir / "schemas" / version / "response_schema.json",
        "request_instance": integration_dir / "schemas" / version / "example_request.json",
        "response_instance": integration_dir / "schemas" / version / "example_response.json",
    }


def _load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as e:
        raise FileNotFoundError(f"File not found: {path}") from e
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in {path}: {e}") from e


def _validate_request(*, schema_path: Path, instance_path: Path | None = None, instance_data: dict[str, Any] | None = None) -> int:
    schema = cast(Any, _load_json(schema_path))

    if instance_data is not None:
        instance = instance_data
        instance_source = "provided payload"
    elif instance_path is not None:
        instance = _load_json(instance_path)
        instance_source = str(instance_path)
    else:
        raise ValueError("Either instance_path or instance_data must be provided")

    try:
        Draft202012Validator.check_schema(schema)
        Draft202012Validator(schema).validate(instance)
        print(f"VALID request: {instance_source} matches {schema_path}")
        return 0
    except (ValidationError, ValueError, FileNotFoundError) as e:
        print(f"INVALID request: {instance_source} does not match {schema_path}")
        print(e)
        return 2


def _validate_response(*, schema_path: Path, instance_path: Path | None = None, instance_data: dict[str, Any] | None = None) -> int:
    schema = cast(Any, _load_json(schema_path))

    if instance_data is not None:
        instance = instance_data
        instance_source = "provided payload"
    elif instance_path is not None:
        instance = _load_json(instance_path)
        instance_source = str(instance_path)
    else:
        raise ValueError("Either instance_path or instance_data must be provided")

    try:
        Draft202012Validator.check_schema(schema)
        Draft202012Validator(schema).validate(instance)
        print(f"VALID response: {instance_source} matches {schema_path}")
        return 0
    except (ValidationError, ValueError, FileNotFoundError) as e:
        print(f"INVALID response: {instance_source} does not match {schema_path}")
        print(e)
        return 2


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Validate BUEM GeoJSON request/response payloads against the versioned JSON Schemas"
    )
    parser.add_argument(
        "--version",
        default=None,
        help="Schema version directory to use (e.g. v2). Default: latest available under schemas/",
    )
    parser.add_argument(
        "--kind",
        choices=["request", "response", "both"],
        default="both",
        help="Validate request, response, or both (default: both)",
    )
    parser.add_argument("--request-schema", type=Path, default=None)
    parser.add_argument("--request-instance", type=Path, default=None)
    parser.add_argument("--response-schema", type=Path, default=None)
    parser.add_argument("--response-instance", type=Path, default=None)

    args = parser.parse_args(argv)

    schemas_dir = _integration_dir() / "schemas"
    version = args.version or _latest_version_dir(schemas_dir)

    defaults = _default_paths(version)

    request_schema_path = (args.request_schema or defaults["request_schema"]).expanduser().resolve()
    request_instance_path = (args.request_instance or defaults["request_instance"]).expanduser().resolve()
    response_schema_path = (args.response_schema or defaults["response_schema"]).expanduser().resolve()
    response_instance_path = (args.response_instance or defaults["response_instance"]).expanduser().resolve()

    exit_codes: list[int] = []
    if args.kind in {"request", "both"}:
        exit_codes.append(
            _validate_request(
                schema_path=request_schema_path,
                instance_path=request_instance_path,
            )
        )
    if args.kind in {"response", "both"}:
        exit_codes.append(
            _validate_response(
                schema_path=response_schema_path,
                instance_path=response_instance_path,
            )
        )

    return 0 if all(code == 0 for code in exit_codes) else 2


if __name__ == "__main__":
    raise SystemExit(main())