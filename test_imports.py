#!/usr/bin/env python3
"""Test script to debug import issues."""

import sys
from pathlib import Path

# Add src to path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

try:
    print("Testing basic import...")
    import buem
    print("✅ buem imported")
    
    print("Testing integration module...")
    import buem.integration
    print("✅ buem.integration imported")
    
    print("Testing schema_manager...")
    from buem.integration.schema_manager import SchemaVersionManager
    print("✅ SchemaVersionManager imported")
    
    print("Testing instance creation...")
    manager = SchemaVersionManager()
    print("✅ SchemaVersionManager instance created")
    
    print("Testing methods...")
    versions = manager.get_available_versions()
    print(f"✅ Available versions: {versions}")
    
    if versions:
        latest = manager.get_latest_version()
        print(f"✅ Latest version: {latest}")
    
    print("\n🎉 All tests passed!")
    
except Exception as e:
    import traceback
    print(f"❌ Error: {e}")
    print(f"Error type: {type(e).__name__}")
    print("Traceback:")
    traceback.print_exc()
    sys.exit(1)