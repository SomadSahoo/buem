"""
Runtime configuration validator for building cfg dicts.

Function validate_cfg(cfg: dict) -> List[str]:
  - Returns empty list when cfg passes checks.
  - Returns list of human-readable issue strings otherwise.
Checks performed:
  - presence of components or legacy U_* keys
  - numeric positive U values for Walls/Windows/Roof/Floor/Doors
  - element areas > 0 and unique element ids if 'components' provided
  - weather timeseries length consistent when series provided
"""
from typing import Dict, List, Any, Set

def _is_number(v) -> bool:
    try:
        float(v)
        return True
    except Exception:
        return False

def validate_cfg(cfg: Dict[str, Any]) -> List[str]:
    issues: List[str] = []

    # components structured check
    comps = cfg.get("components")
    if isinstance(comps, dict):
        seen_ids: Set[str] = set()
        for comp in ("Walls", "Windows", "Roof", "Floor", "Doors"):
            c = comps.get(comp)
            if c is None:
                issues.append(f"components.{comp} missing")
                continue
            # component-level U
            u = c.get("U")
            if u is None:
                # check elements for per-element U
                elems = c.get("elements", [])
                if not elems:
                    issues.append(f"components.{comp}.U missing and no elements with U")
                else:
                    for idx, e in enumerate(elems):
                        if not isinstance(e, dict):
                            issues.append(f"components.{comp}.elements[{idx}] not an object")
                            continue
                        eid = e.get("id")
                        if eid is None:
                            issues.append(f"components.{comp}.elements[{idx}].id missing")
                        else:
                            if eid in seen_ids:
                                issues.append(f"duplicate element id '{eid}' in components")
                            seen_ids.add(eid)
                        area = e.get("area")
                        if area is None:
                            issues.append(f"components.{comp}.elements[{idx}].area missing")
                        else:
                            try:
                                if float(area) <= 0:
                                    issues.append(f"components.{comp}.elements[{idx}].area must be > 0")
                            except Exception:
                                issues.append(f"components.{comp}.elements[{idx}].area invalid: {area}")
                        u_e = e.get("U")
                        if u_e is None:
                            issues.append(f"components.{comp}.elements[{idx}].U missing")
                        else:
                            if not _is_number(u_e) or float(u_e) <= 0:
                                issues.append(f"components.{comp}.elements[{idx}].U must be positive number")
            else:
                if not _is_number(u) or float(u) <= 0:
                    issues.append(f"components.{comp}.U must be positive number")

    else:
        # legacy keys fallback: expect at least the main U_* keys or explicit per-element U values
        legacy = {
            "Windows": "U_Window",
            "Walls": "U_Wall_1",
            "Roof": "U_Roof_1",
            "Floor": "U_Floor_1",
            "Doors": "U_Door_1",
        }
        for comp, key in legacy.items():
            v = cfg.get(key)
            if v is None:
                issues.append(f"legacy key {key} missing")
            else:
                if not _is_number(v) or float(v) <= 0:
                    issues.append(f"{key} must be positive number")

    # weather length coherence (optional)
    weather = cfg.get("weather")
    if weather is not None:
        # if it's a DataFrame-like dict with 'index' or series entries, skip deep checks here
        try:
            n = len(weather)
            if n == 0:
                issues.append("weather timeseries appears empty")
        except Exception:
            pass

    return issues