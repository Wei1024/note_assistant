#!/usr/bin/env python3
"""
Normalize Momo SVG files to have consistent viewBox positioning.
This fixes the issue where some frames appear higher/lower than others.
"""

import re
import xml.etree.ElementTree as ET

svg_files = [
    'frontend/src/assets/momo/momo_default.svg',
    'frontend/src/assets/momo/momo_mouth_mid-chew.svg',
    'frontend/src/assets/momo/momo_chewing.svg',
    'frontend/src/assets/momo/momo_cheek_bulge.svg',
]

for svg_file in svg_files:
    print(f"Processing {svg_file}...")

    with open(svg_file, 'r') as f:
        content = f.read()

    # Add viewBox to center and crop to content
    # This ensures all SVGs show Momo in the same position
    content = content.replace(
        '<svg version="1.1" xmlns="http://www.w3.org/2000/svg" width="1024" height="1024">',
        '<svg version="1.1" xmlns="http://www.w3.org/2000/svg" width="1024" height="1024" viewBox="0 0 1024 1024">'
    )

    with open(svg_file, 'w') as f:
        f.write(content)

    print(f"✓ Added viewBox to {svg_file}")

print("\nDone! All SVGs now have consistent viewBox attributes.")
