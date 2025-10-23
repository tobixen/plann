#!/usr/bin/env python3
"""
Test script for configuration dialog
"""

import sys
import os

# Add plann to path
sys.path.insert(0, os.path.dirname(__file__))

from plann.gui import ConfigDialog

if __name__ == "__main__":
    print("Testing ConfigDialog...")
    dialog = ConfigDialog()
    result = dialog.show()

    if result:
        print("\n✓ Configuration saved successfully!")
        print(f"Config: {result}")
    else:
        print("\n✗ Configuration cancelled")
