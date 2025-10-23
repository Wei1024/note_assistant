# Momo Setup Scripts

This directory contains scripts used to set up and prepare Momo assets for the application.

## Files

### Vectorization Scripts
- `vectorize_all_momos.py` - Main script to vectorize all Momo PNG images to SVG
- `vectorize_momo.py` - Original single-image vectorization script
- `vectorize_momo_clean.py` - Clean vectorization with artifact reduction
- `normalize_momo_svgs.py` - Normalize SVG viewBoxes for consistent positioning

### Example Files
- `MomoEating.jsx.example` - React/JSX example implementation (for reference only)

## Usage

### Vectorizing New Momo Images

1. Place PNG images in the project root
2. Run the vectorization script:
```bash
source .venv/bin/activate
python scripts/momo_setup/vectorize_all_momos.py
```

3. Copy resulting SVGs to frontend:
```bash
cp *.svg frontend/src/assets/momo/
```

## Current Momo States

The app uses these Momo SVG files (located in `frontend/src/assets/momo/`):
- `momo_default.svg` - Resting state
- `momo_happy.svg` - User is typing (excited)
- `momo_mouth_open.svg` - Ready to eat (hovering)
- `momo_mouth_mid-chew.svg` - Mid-chew animation frame
- `momo_chewing.svg` - Full chew animation frame
- `momo_cheek_bulge.svg` - Cheek bulge animation frame

## Notes

- All scripts require vtracer: `pip install vtracer`
- SVGs are automatically processed to remove white backgrounds
- Settings are optimized for smooth curves and clean edges
