"""Allow ``python -m buem.weather`` to run the pipeline standalone.

This entry point replaces the ``buem weather`` CLI command on servers
where the full buem package is not installed.  All arguments are the same.

Usage examples::

    # Show resolved configuration
    python -m buem.weather info

    # Validate that required tools are available
    python -m buem.weather validate

    # Run the full pipeline (all months for the configured year)
    python -m buem.weather run

    # Single-month test run
    python -m buem.weather run --months 1

    # Override year and working directory
    python -m buem.weather run --year 2017 --work-dir /scratch/weather
"""

from __future__ import annotations

import argparse
import logging
import sys


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m buem.weather",
        description="COSMO-REA6 weather processing pipeline (standalone).",
    )
    sub = parser.add_subparsers(dest="command")

    # --- info ---
    sub.add_parser("info", help="Show resolved pipeline configuration.")

    # --- validate ---
    sub.add_parser("validate", help="Check required tools and libraries.")

    # --- run ---
    run_p = sub.add_parser("run", help="Execute the full pipeline.")
    run_p.add_argument("--year", type=int, default=None, help="Year to process.")
    run_p.add_argument(
        "--months", type=int, nargs="+", default=None,
        help="Month(s) to process (e.g. --months 1 2 3).",
    )
    run_p.add_argument("--work-dir", default=None, help="Override COSMO_WORK_DIR.")
    run_p.add_argument("--output", default=None, help="Output NetCDF path.")
    run_p.add_argument(
        "--no-wind-components", action="store_true",
        help="Exclude raw U_10M/V_10M from output.",
    )
    run_p.add_argument(
        "--complevel", type=int, default=5,
        help="zlib compression level (default: 5).",
    )
    run_p.add_argument(
        "--skip-download", action="store_true",
        help="Skip download step (assume .grb.bz2 files exist).",
    )
    run_p.add_argument(
        "--skip-decompress", action="store_true",
        help="Skip decompress step (assume .grb files exist).",
    )
    run_p.add_argument(
        "--cleanup", action="store_true",
        help="Remove downloaded and decompressed files after export.",
    )

    return parser


def main(argv: list[str] | None = None) -> None:
    parser = _build_parser()
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    if args.command is None:
        parser.print_help()
        sys.exit(1)

    if args.command == "info":
        from .config import ATTRIBUTES, get_config

        cfg = get_config()
        print("COSMO-REA6 Weather Pipeline Configuration")
        print("=" * 50)
        keys = [
            "year", "months", "attributes", "work_dir", "download_dir",
            "decompress_dir", "output_dir", "base_url", "ncores",
        ]
        for key in keys:
            val = cfg.get(key, "")
            print(f"  {key:<18s}  {val}")
        print()
        print("Attribute definitions:")
        for name, meta in ATTRIBUTES.items():
            print(
                f"  {name:<16s}  {meta['unit_raw']:>6s} → "
                f"{meta['unit_target']:<6s}  {meta['description']}"
            )

    elif args.command == "validate":
        from .pipeline import validate_environment

        issues = validate_environment()
        if issues:
            print("Weather pipeline environment issues:")
            for issue in issues:
                print(f"  [!] {issue}")
            sys.exit(1)
        else:
            print("Weather pipeline environment OK — all tools available.")

    elif args.command == "run":
        from pathlib import Path

        from .pipeline import run_pipeline

        nc_path = run_pipeline(
            year=args.year,
            months=args.months,
            work_dir=Path(args.work_dir) if args.work_dir else None,
            output_path=Path(args.output) if args.output else None,
            include_wind_components=not args.no_wind_components,
            complevel=args.complevel,
            skip_download=args.skip_download,
            skip_decompress=args.skip_decompress,
            cleanup=args.cleanup,
        )
        print(f"\nOutput: {nc_path}")


if __name__ == "__main__":
    main()
