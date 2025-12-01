from flask import Blueprint, request, jsonify, current_app
import json
import time
import traceback
import requests
import logging

from buem.config.cfg_building import CfgBuilding
from buem.main import run_model
from buem.config.validator import validate_cfg

bp = Blueprint("model_api", __name__, url_prefix="/api")
logger = logging.getLogger(__name__)

def _to_serializable_timeseries(times_index, arr):
    return {
        "index": [ts.isoformat() for ts in list(times_index)],
        "values": [float(x) for x in list(arr)],
    }

@bp.route("/run", methods=["POST"])
def run_building_model():
    start = time.time()
    try:
        payload = request.get_json(force=True, silent=True) or {}
        cfgb = CfgBuilding(json.dumps(payload))
        cfg = cfgb.to_cfg_dict()

        # run centralized validator (returns list of issues)
        issues = validate_cfg(cfg)
        if issues:
            return jsonify({"status": "error", "error": "validation_failed", "issues": issues}), 400

        # call centralized runner (allow caller to request MILP)
        use_milp = bool(payload.get("use_milp", False))
        res = run_model(cfg, plot=False, use_milp=use_milp)
        times = res["times"]
        heating = res["heating"]
        cooling = res["cooling"]

        result = {
            "heating": _to_serializable_timeseries(times, heating),
            "cooling": _to_serializable_timeseries(times, cooling),
            "meta": {"n_points": len(times), "elapsed_s": round(res.get("elapsed_s", time.time()-start), 3)},
        }

        forward_url = payload.get("forward_url")
        if forward_url:
            try:
                r = requests.post(forward_url, json=result, timeout=30)
                result["forward"] = {"status_code": r.status_code, "response_text": r.text}
            except Exception as ex:
                current_app.logger.exception("Forwarding failed")
                result["forward"] = {"error": str(ex)}

        current_app.logger.info("Model run completed, points=%d elapsed=%.3fs", len(times), result["meta"]["elapsed_s"])
        return jsonify({"status": "ok", "result": result}), 200

    except ValueError as ve:
        # validation or other expected errors -> return 400
        current_app.logger.warning("Validation error: %s", str(ve))
        return jsonify({"status": "error", "error": "validation_failed", "message": str(ve)}), 400

    except Exception as exc:
        current_app.logger.exception("API run failed")
        return jsonify({"status": "error", "error": str(exc), "trace": traceback.format_exc()}), 500