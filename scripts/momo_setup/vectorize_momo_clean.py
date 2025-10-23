#!/usr/bin/env python3
"""Convert Momo_sitting.png to SVG with cleaner settings."""

import vtracer

# Convert the image to SVG with settings optimized to reduce artifacts
input_path = "Momo_sitting.png"
output_path = "Momo_sitting_clean.svg"

print(f"Converting {input_path} to {output_path} with cleaner settings...")

vtracer.convert_image_to_svg_py(
    input_path,
    output_path,
    colormode='color',        # Use color mode
    hierarchical='stacked',   # How to layer paths
    mode='spline',           # Use spline curves for smoother result
    filter_speckle=8,        # Increased from 4 - remove more small artifacts
    color_precision=8,       # Increased color precision for better accuracy
    layer_difference=32,     # Increased from 16 - more aggressive layer merging
    corner_threshold=80,     # Increased from 60 - smoother corners
    length_threshold=8.0,    # Increased from 4.0 - filter out shorter paths
    splice_threshold=60,     # Increased from 45 - more aggressive path splicing
    path_precision=2         # Reduced from 3 - simpler paths
)

print(f"✓ Successfully created {output_path}")
