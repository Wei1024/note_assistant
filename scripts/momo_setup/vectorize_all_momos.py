#!/usr/bin/env python3
"""Convert all Momo PNG files to SVG using vtracer."""

import vtracer
import os

# List of Momo images to convert
momo_images = [
    "momo_default.png",
    "momo_mouth_open.png",
    "momo_happy.png",
    "momo_mouth_mid-chew.png",
    "momo_chewing.png",
    "momo_cheek_bulge.png"
]

# Vectorization settings optimized for smoother lines
settings = {
    'colormode': 'color',
    'hierarchical': 'stacked',
    'mode': 'spline',
    'filter_speckle': 4,       # Reduced - keep more detail
    'color_precision': 6,      # Balanced color accuracy
    'layer_difference': 16,    # Less aggressive merging for smoother edges
    'corner_threshold': 120,   # Much smoother corners
    'length_threshold': 3.0,   # Keep more paths for detail
    'splice_threshold': 80,    # More aggressive splicing for smoother curves
    'path_precision': 8        # Higher precision for smoother curves
}

print("Converting Momo images to SVG...\n")

for image in momo_images:
    if not os.path.exists(image):
        print(f"⚠️  Warning: {image} not found, skipping...")
        continue

    output = image.replace('.png', '.svg')
    print(f"Converting {image} → {output}")

    try:
        vtracer.convert_image_to_svg_py(
            image,
            output,
            **settings
        )

        # Remove white/light background from the SVG
        with open(output, 'r') as f:
            svg_content = f.read()

        import re
        # Remove paths with light/white fills (F8F8F8, FEFEFE, FFFFFF, etc.)
        # Match any fill color that starts with F and is very light
        svg_content = re.sub(r'<path[^>]*fill="#F[0-9A-F]F[0-9A-F]F[0-9A-F]"[^>]*?/>\n?', '', svg_content)

        with open(output, 'w') as f:
            f.write(svg_content)

        print(f"✓ Successfully created {output} (background removed)\n")
    except Exception as e:
        print(f"✗ Error converting {image}: {e}\n")

print("Done! You now have:")
print("- momo_default.svg")
print("- momo_mouth_open.svg")
print("- momo_happy.svg")
print("- momo_mouth_mid-chew.svg")
print("- momo_chewing.svg")
print("\n5-frame smooth animation sequence ready!")
print("Suggested order: default → mouth_open → happy → mid-chew → chewing → (loop back)")
