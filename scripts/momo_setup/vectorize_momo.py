#!/usr/bin/env python3
"""Convert Momo_sitting.png to SVG using vtracer."""

import vtracer

# Convert the image to SVG
input_path = "Momo_sitting.png"
output_path = "Momo_sitting.svg"

print(f"Converting {input_path} to {output_path}...")

vtracer.convert_image_to_svg_py(
    input_path,
    output_path,
    colormode='color',        # Use color mode for the decorative image
    hierarchical='stacked',   # How to layer paths
    mode='spline',           # Use spline curves for smoother result
    filter_speckle=4,        # Remove small speckles (4px threshold)
    color_precision=6,       # Color precision (higher = more colors)
    layer_difference=16,     # Layer difference threshold
    corner_threshold=60,     # Corner detection threshold
    length_threshold=4.0,    # Minimum path length
    splice_threshold=45,     # Path splice threshold
    path_precision=3         # Path coordinate precision
)

print(f"✓ Successfully created {output_path}")
