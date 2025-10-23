#!/usr/bin/env python3
"""Convert stickynotes.png to SVG to extract border patterns."""

import vtracer

# Convert the sticky note image to SVG
input_path = "../../frontend/src/assets/momo_draft/stickynotes.png"
output_path = "../../frontend/src/assets/momo_draft/stickynotes.svg"

print(f"Converting {input_path} to {output_path}...")

vtracer.convert_image_to_svg_py(
    input_path,
    output_path,
    colormode='color',        # Use color mode to preserve border colors
    hierarchical='stacked',   # Layer paths properly
    mode='spline',           # Use spline curves for smooth borders
    filter_speckle=6,        # Remove small artifacts
    color_precision=6,       # Good color accuracy
    layer_difference=16,     # Moderate layer merging
    corner_threshold=60,     # Preserve sharp corners in patterns
    length_threshold=4.0,    # Keep detailed border patterns
    splice_threshold=45,     # Moderate path splicing
    path_precision=3         # Detailed paths for border patterns
)

print(f"✓ Successfully created {output_path}")
print("Now you can extract the border pattern paths from the SVG!")
