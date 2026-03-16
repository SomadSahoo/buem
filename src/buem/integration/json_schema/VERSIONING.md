# BUEM--EnerPlanET API Schema Versioning Policy

This document defines how schema versions are managed for the
BUEM--EnerPlanET integration.

The JSON schemas in this repository represent the authoritative contract
between EnerPlanET (client) and the BUEM microservice (server).

------------------------------------------------------------------------

## Versioning Approach

Schemas use **semantic versioning** (MAJOR.MINOR.PATCH) via Git releases.

- `schemas/` — always contains the current released version
- `schemas/v1/`, `schemas/v2/`, `schemas/v3/` — archived snapshots
- Git releases (`v1.0.0`, `v2.0.0`, etc.) are the authoritative version tags
- Any historical version is accessible via `git checkout <tag> -- schemas/`

------------------------------------------------------------------------

## Semantic Versioning Rules

### MAJOR — breaking change, client must update

- Required fields added or removed
- Field renamed or relocated
- Field type changes (including bare number to measurement object)
- Validation constraints become stricter
- Semantic meaning of a field changes

### MINOR — backwards compatible addition

- New optional field added
- New allowed unit added to an existing quantity type
- New optional node added (e.g. new section under `buem`)

### PATCH — no validation change

- Description or documentation text corrected
- Example values updated
- Whitespace or formatting only

------------------------------------------------------------------------

## Release Process

1. Make changes to `schemas/` (flat directory)
2. Validate both schemas against their example files
3. Update `CHANGELOG.md`
4. Commit and create a Git release with the new version tag

```bash
# Validate before releasing
python -c "
import json
from jsonschema import Draft202012Validator
for name in ['request', 'response']:
    schema  = json.load(open(f'schemas/{name}_schema.json'))
    example = json.load(open(f'schemas/example_{name}.json'))
    errs = list(Draft202012Validator(schema).iter_errors(example))
    print(f'{name}: OK' if not errs else [e.message for e in errs])
"

# Create release
gh release create v3.1.0 --title "v3.1.0" --notes "..." \
  schemas/request_schema.json \
  schemas/response_schema.json \
  schemas/example_request.json \
  schemas/example_response.json
```

------------------------------------------------------------------------

## What Counts as a Breaking Change -- v2 to v3 Examples

- `building_attributes` replaced by four nodes: `building`, `envelope`,
  `thermal`, `solver`
- `latitude`/`longitude` removed from `buem` -- now read from
  `feature.geometry.coordinates` only
- All measurable quantities changed from bare numbers to
  `{ "value": number, "unit": string }` objects
- `components` nested object replaced by flat `envelope.elements[]`
- `child_components` legacy format removed
- Energy summary fields renamed (`total_kwh` to `total`, `max_kw` to `max`, etc.)

------------------------------------------------------------------------

## Released Versions

### v3.0.0 (2026-03) -- Current

Migration from v2: Breaking changes. See CHANGELOG.md for full details.

Key changes:
- Separation of concerns: `building`, `envelope`, `thermal`, `solver` nodes
- Location sourced exclusively from GeoJSON geometry
- Unit-aware `{ value, unit }` measurement types throughout
- Flat `envelope.elements[]` with user-defined ids, unlimited per type
- Thermal properties decoupled from geometry via `thermal.element_properties[]`
- TABULA-aligned thermal parameters exposed as optional fields
- `metadata` formalised as required top-level response field

Archived snapshot: `schemas/v3/`

### v2.0.0 (2026-02) -- Deprecated

Migration from v1: Breaking changes.

Key changes:
- Introduced structured `$defs`
- Optional elevation in geometry (3D coordinates)
- Replaced loose `building_attributes` with structured nested schema
- Added nested component model (Walls/Roof/Floor/Windows/Doors/Ventilation)
- Introduced `use_milp` control flag
- Stricter validation rules

Archived snapshot: `schemas/v2/`

### v1.0.0 (2025-11) -- Deprecated

Initial schema version. Minimal structure, loose typing, flat child
component model, strictly 2D geometry.

Archived snapshot: `schemas/v1/`

------------------------------------------------------------------------

## Governance

EnerPlanET maintains this contract repository.

Any proposed schema change must:

1. Be documented in CHANGELOG.md
2. Be reviewed before merging
3. Be validated using JSON Schema validation tools
4. Follow semver -- increment MAJOR for breaking, MINOR for additions,
   PATCH for documentation only

------------------------------------------------------------------------

This policy ensures stable integration and controlled evolution of the
BUEM--EnerPlanET API contract.
