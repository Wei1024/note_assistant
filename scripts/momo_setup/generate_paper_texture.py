#!/usr/bin/env python3
"""
Generate a realistic paper texture for the sticky note component.
Uses PIL to create a noise texture that looks like paper grain.
"""

from PIL import Image, ImageDraw, ImageFilter
import random
import base64
from io import BytesIO

# Create a small texture (will be tiled)
size = 200
img = Image.new('RGBA', (size, size), (255, 255, 255, 0))
pixels = img.load()

# Generate random noise for paper grain
random.seed(42)  # Consistent texture
for x in range(size):
    for y in range(size):
        # Random noise with varying intensity
        noise = random.randint(-15, 15)

        # More noise in some areas (like paper fibers)
        if random.random() < 0.1:
            noise = random.randint(-25, 25)

        # Apply noise as slight darkness/lightness
        if noise > 0:
            # Lighter spots (white fibers)
            alpha = min(int(abs(noise) * 1.5), 20)
            pixels[x, y] = (255, 255, 255, alpha)
        else:
            # Darker spots (texture variation)
            alpha = min(int(abs(noise) * 1.2), 15)
            pixels[x, y] = (0, 0, 0, alpha)

# Apply slight blur to make it more organic
img = img.filter(ImageFilter.GaussianBlur(radius=0.5))

# Save as PNG
output_path = "../../frontend/src/assets/paper-texture.png"
img.save(output_path, 'PNG')
print(f"✓ Created paper texture: {output_path}")

# Also generate base64 for inline CSS (optional)
buffered = BytesIO()
img.save(buffered, format="PNG")
img_str = base64.b64encode(buffered.getvalue()).decode()

# Write CSS snippet
css_snippet = f"""
/* Paper texture as data URL (can be inlined in CSS) */
background-image: url('data:image/png;base64,{img_str}');
background-repeat: repeat;
background-size: 200px 200px;
"""

css_path = "../../frontend/src/assets/paper-texture.css"
with open(css_path, 'w') as f:
    f.write(css_snippet)

print(f"✓ Created CSS snippet: {css_path}")
print(f"\nData URL length: {len(img_str)} characters")
print("\nYou can either:")
print("1. Use the PNG file: background-image: url('@/assets/paper-texture.png');")
print("2. Copy the data URL from paper-texture.css for inline use")
