# buem-contract

Contract definition and JSON schemas for the integration between\
**EnerPlanET backend** and the **BUEM time-series microservice**.

This repository defines the authoritative request and response formats
used when EnerPlanET communicates with the BUEM container.

The BUEM microservice runs internally within the EnerPlanET Docker stack
and is not exposed externally.

------------------------------------------------------------------------

## Scope

This repository defines:

- The JSON structure of request payloads sent to BUEM
- The JSON structure of response payloads returned by BUEM
- Versioning rules for schema evolution
- Example payloads
- Change documentation

This repository does **not** contain implementation code.

------------------------------------------------------------------------

## Microservice Contract

The BUEM container must:

- Expose `POST /timeseries`
- Accept request payloads matching `request_schema.json`
- Return response payloads matching `response_schema.json`
- Preserve all input fields
- Add computed `thermal_load_profile`
- Expose `GET /health`
- Bind to `0.0.0.0` inside the container

------------------------------------------------------------------------

## Schema Versioning

Schemas are versioned using version folders:

    schemas/
      v1/
      v2/
      v3/

Each version folder is immutable once released.

Breaking changes require a new version folder.

EnerPlanET validates both request and response payloads against the
corresponding schema version.

Clients should always use the latest agreed version unless explicitly
required otherwise.

For detailed rules see `VERSIONING.md`.

------------------------------------------------------------------------

## Version Folder Content

Each version folder contains:

- `request_schema.json`
- `response_schema.json`
- `example_request.json`
- `example_response.json`

Optional: - Version-specific notes in `CHANGELOG.md`

------------------------------------------------------------------------

## Schema Validation

Schemas and example payloads can be validated using JSON Schema tools.

Example using Python:

```python
import json
from jsonschema import validate

with open("schemas/v2/request_schema.json") as f:
    schema = json.load(f)

with open("schemas/v2/example_request.json") as f:
    payload = json.load(f)

validate(instance=payload, schema=schema)
print("Valid.")
```

Validation must pass before schema versions are released.

## Schema Visualization

Helpful for understanding complex nested structures and relationships between fields it's recommended to use [jsoncrack](https://jsoncrack.com) to visualize the schema structure.

> [!TIP]
> If you are using VS Code, the [JSON Schema extension](https://marketplace.visualstudio.com/items?itemName=AykutSarac.jsoncrack-vscode) can provide inline validation and visualization.