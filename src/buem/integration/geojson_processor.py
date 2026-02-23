"""
Process GeoJSON payloads: extract attributes, run thermal model, return results.
"""
from typing import Any, Callable, Dict, List, Optional
from datetime import datetime, timezone
from pathlib import Path
import time
import uuid
import json
import gzip
import logging
import numpy as np
import pandas as pd
from flask import current_app

from buem.integration.attribute_builder import AttributeBuilder
from buem.config.cfg_building import CfgBuilding
from buem.main import run_model

logger = logging.getLogger(__name__)


class GeoJsonProcessor:
    """
    Process GeoJSON FeatureCollection with building energy model specifications.
    
    Workflow:
    1. Extract building attributes from GeoJSON feature
    2. Merge with database/defaults via AttributeBuilder
    3. Run thermal model (heating/cooling loads)
    4. Compute summary statistics
    5. Save timeseries .gz file (optional)
    6. Return results in GeoJSON format
    
    Parameters
    ----------
    payload : Dict[str, Any]
        GeoJSON FeatureCollection or single Feature.
    include_timeseries : bool, optional
        Save hourly timeseries to .gz file (default: False).
    db_fetcher : Callable, optional
        Function(building_id) -> Dict of additional attributes.
    result_save_dir : str or Path, optional
        Directory for saving .gz files (default: env BUEM_RESULTS_DIR).
    """
    
    def __init__(
        self,
        payload: Dict[str, Any],
        include_timeseries: bool = False,
        db_fetcher: Optional[Callable[[str], Dict[str, Any]]] = None,
        result_save_dir: Optional[str] = None,
    ):
        self.payload = payload
        self.include_timeseries = include_timeseries
        self.db_fetcher = db_fetcher
        
        # Result save directory
        if result_save_dir:
            self.result_save_dir = Path(result_save_dir)
        else:
            import os
            default_dir = Path(__file__).resolve().parents[1] / "results"
            self.result_save_dir = Path(os.environ.get("BUEM_RESULTS_DIR", str(default_dir)))
    
    def process(self) -> Dict[str, Any]:
        """
        Process all features and return GeoJSON FeatureCollection with results.
        
        Returns
        -------
        Dict[str, Any]
            GeoJSON FeatureCollection with thermal_load_profile added to each feature.
        """
        start_time = time.time()
        
        # Normalize to FeatureCollection
        if self.payload.get("type") == "Feature":
            features = [self.payload]
        elif self.payload.get("type") == "FeatureCollection":
            features = self.payload.get("features", [])
        else:
            raise ValueError("Payload must be GeoJSON Feature or FeatureCollection")
        
        # Process each feature
        out_features = []
        for feat in features:
            try:
                processed = self._process_single_feature(feat)
                out_features.append(processed)
            except Exception as exc:
                logger.exception(f"Feature {feat.get('id')} failed: {exc}")
                # Include error in feature
                feat.setdefault("properties", {}).setdefault("buem", {})["error"] = str(exc)
                out_features.append(feat)
        
        return {
            "type": "FeatureCollection",
            "features": out_features,
            "processed_at": datetime.now(timezone.utc).isoformat(),
            "processing_elapsed_s": round(time.time() - start_time, 3),
        }
    
    def _process_single_feature(self, feature: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process single GeoJSON feature: build attributes, run model, add results.
        
        Parameters
        ----------
        feature : Dict[str, Any]
            GeoJSON Feature with properties.buem.building_attributes.
        
        Returns
        -------
        Dict[str, Any]
            Feature with added thermal_load_profile in properties.buem.
        """
        props = feature.setdefault("properties", {})
        buem = props.setdefault("buem", {})
        building_id = feature.get("id")
        payload_attrs = buem.get("building_attributes", {})
        
        #  Build complete attributes
        builder = AttributeBuilder(
            payload_attrs=payload_attrs,
            building_id=building_id,
            db_fetcher=self.db_fetcher
        )
        merged_attrs = builder.build()
        
        # Convert to model config
        cfg = CfgBuilding(merged_attrs).to_cfg_dict()
        
        # Run thermal model
        use_milp = bool(buem.get("use_milp", False))
        start = time.time()
        res = run_model(cfg, plot=False, use_milp=use_milp)
        elapsed = time.time() - start
        
        # Extract results
        times = res.get("times", [])
        heating = np.asarray(res.get("heating", []), dtype=float)
        cooling = np.asarray(res.get("cooling", []), dtype=float)
        
        # Electricity: prefer model output, else use cfg elecLoad
        if "electricity" in res:
            electricity = np.asarray(res["electricity"], dtype=float)
        else:
            elec_cfg = cfg.get("elecLoad")
            if isinstance(elec_cfg, pd.Series):
                electricity = elec_cfg.values.astype(float)
            else:
                electricity = np.asarray(elec_cfg or [], dtype=float)
        
        # Sanitize NaN/inf
        heating = np.nan_to_num(heating, nan=np.nan, posinf=1e9, neginf=-1e9)
        cooling = np.nan_to_num(cooling, nan=np.nan, posinf=1e9, neginf=-1e9)
        electricity = np.nan_to_num(electricity, nan=np.nan, posinf=1e9, neginf=-1e9)
        
        # Check for NaN
        nan_h, nan_c, nan_e = np.isnan(heating).sum(), np.isnan(cooling).sum(), np.isnan(electricity).sum()
        if nan_h or nan_c or nan_e:
            logger.warning(
                f"Feature {building_id}: NaN in results (heat={nan_h}/{heating.size}, "
                f"cool={nan_c}/{cooling.size}, elec={nan_e}/{electricity.size})"
            )
        
        # Build summary profile
        profile = self._build_summary(times, heating, cooling, electricity, elapsed)
        
        # Save timeseries if requested
        if self.include_timeseries and len(times):
            try:
                fname = self._save_timeseries(times, heating, cooling, electricity)
                profile["timeseries_file"] = f"/api/files/{fname}"
            except Exception as exc:
                logger.exception(f"Timeseries save failed: {exc}")
        
        # Attach results (do not include large arrays in response)
        buem["thermal_load_profile"] = profile
        
        return feature
    
    def _build_summary(
        self, times, heating, cooling, electricity, elapsed
    ) -> Dict[str, Any]:
        """Compute summary statistics from timeseries arrays."""
        safe_sum = lambda arr: float(np.nansum(arr)) if len(arr) else 0.0
        safe_max = lambda arr: float(np.nanmax(arr)) if len(arr) else 0.0
        safe_min = lambda arr: float(np.nanmin(arr)) if len(arr) else 0.0

        # Handle times (may be DatetimeIndex, list, or empty)
        has_times = False
        if isinstance(times, pd.DatetimeIndex):
            has_times = not times.empty
        elif times is not None:
            has_times = len(times) > 0       

        return {
            "heating_total_kWh": safe_sum(heating),
            "heating_peak_kW": safe_max(heating),
            "cooling_total_kWh": abs(safe_sum(cooling)),
            "cooling_peak_kW": abs(safe_min(cooling)),
            "electricity_total_kWh": safe_sum(electricity),
            "electricity_peak_kW": safe_max(electricity),
            "start_time": times[0].isoformat() if has_times else None,
            "end_time": times[-1].isoformat() if has_times else None,
            "n_points": len(times) if has_times else 0,
            "elapsed_s": round(elapsed, 3),
        }
    
    def _save_timeseries(self, times, heating, cooling, electricity) -> str:
        """
        Save timeseries as gzipped JSON.
        
        Returns
        -------
        str
            Filename (e.g., 'buem_ts_abc123.json.gz').
        """
        self.result_save_dir.mkdir(parents=True, exist_ok=True)
        fname = f"buem_ts_{uuid.uuid4().hex}.json.gz"
        full_path = self.result_save_dir / fname

        # Convert times to list of ISO strings (handles DatetimeIndex or list)
        if isinstance(times, pd.DatetimeIndex):
            time_list = [t.isoformat() for t in times]
        else:
            time_list = [t.isoformat() for t in times]       

        payload = {
            "index": time_list,
            "heat": [float(x) for x in heating.tolist()],
            "cool": [float(x) for x in cooling.tolist()],
            "electricity": [float(x) for x in electricity.tolist()] if len(electricity) else [],
        }
        
        with gzip.open(full_path, "wt", encoding="utf-8") as gz:
            json.dump(payload, gz, indent=None)
        
        logger.info(f"Saved timeseries: {full_path}")
        return fname