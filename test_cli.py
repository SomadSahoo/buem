#!/usr/bin/env python3
"""Simple test of the CLI without complex imports."""

import sys
from pathlib import Path

# Add src to path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

def test_schema_cli():
    """Test the CLI functionality."""
    try:
        # Simple validation using the enhanced schema validator
        from buem.integration.schema_validator import main
        
        print("Testing schema CLI help...")
        result = main(["--help"])
        print(f"Help command result: {result}")
        
    except SystemExit as e:
        if e.code == 0:
            print("✅ Help command worked (expected SystemExit with code 0)")
        else:
            print(f"❌ Help command failed with code: {e.code}")
    except ImportError as e:
        print(f"❌ Import error: {e}")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_schema_cli()