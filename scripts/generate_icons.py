"""
Generates placeholder Tauri icons for ACOS.
Run: python scripts/generate_icons.py
Replace frontend/src-tauri/icons/icon.png with a real logo, then re-run.
"""
from __future__ import annotations

from pathlib import Path

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    raise SystemExit("Install Pillow first: pip install Pillow")

ICONS_DIR = Path(__file__).parent.parent / "frontend" / "src-tauri" / "icons"
ICONS_DIR.mkdir(parents=True, exist_ok=True)

BRAND_BG = (15, 15, 20)
BRAND_FG = (99, 102, 241)    # indigo-500


def draw_icon(size: int) -> Image.Image:
    img = Image.new("RGBA", (size, size), BRAND_BG + (255,))
    draw = ImageDraw.Draw(img)
    margin = size // 6
    draw.rounded_rectangle(
        [margin, margin, size - margin, size - margin],
        radius=size // 5,
        fill=BRAND_FG + (255,),
    )
    # Draw "A" lettermark
    text_size = max(size // 2, 12)
    try:
        font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", text_size)
    except Exception:
        font = ImageFont.load_default()
    bbox = draw.textbbox((0, 0), "A", font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    draw.text(
        ((size - tw) // 2 - bbox[0], (size - th) // 2 - bbox[1]),
        "A",
        fill=(255, 255, 255, 255),
        font=font,
    )
    return img


# PNG sizes required by tauri.conf.json
for px in [32, 128]:
    icon = draw_icon(px)
    icon.save(ICONS_DIR / f"{px}x{px}.png")
    print(f"  ✓ {px}x{px}.png")

# 128x128@2x (256px physical, labelled @2x)
icon_2x = draw_icon(256)
icon_2x.save(ICONS_DIR / "128x128@2x.png")
print("  ✓ 128x128@2x.png")

# macOS .icns
icns_sizes = [16, 32, 64, 128, 256, 512, 1024]
from PIL import Image as _PILImage  # noqa: E402
icns_images: dict[str, _PILImage.Image] = {}
for px in icns_sizes:
    icns_images[f"isize{px}"] = draw_icon(px)

largest = draw_icon(1024)
largest.save(ICONS_DIR / "icon.png")  # base icon
print("  ✓ icon.png")

# Build .icns using iconutil (macOS only)
# iconutil requires "icon_NxN.png" and "icon_NxN@2x.png" naming convention.
import subprocess  # noqa: E402
import tempfile  # noqa: E402

tmp = Path(tempfile.mkdtemp()) / "icon.iconset"
tmp.mkdir()
# Each tuple: (logical_size, physical_1x_px, physical_2x_px)
iconset_sizes = [
    (16, 16, 32),
    (32, 32, 64),
    (128, 128, 256),
    (256, 256, 512),
    (512, 512, 1024),
]
for logical, px1x, px2x in iconset_sizes:
    draw_icon(px1x).save(tmp / f"icon_{logical}x{logical}.png")
    draw_icon(px2x).save(tmp / f"icon_{logical}x{logical}@2x.png")
result = subprocess.run(
    ["iconutil", "-c", "icns", str(tmp), "-o", str(ICONS_DIR / "icon.icns")],
    capture_output=True,
)
if result.returncode == 0:
    print("  ✓ icon.icns")
else:
    print(f"  ⚠ iconutil failed: {result.stderr.decode()}. Create icon.icns manually.")

# Windows .ico (multi-size)
ico_images = [draw_icon(px) for px in [16, 32, 48, 64, 128, 256]]
ico_images[0].save(
    ICONS_DIR / "icon.ico",
    format="ICO",
    append_images=ico_images[1:],
    sizes=[(px, px) for px in [16, 32, 48, 64, 128, 256]],
)
print("  ✓ icon.ico")

print(f"\nIcons written to {ICONS_DIR}")
print("Replace frontend/src-tauri/icons/icon.png with a real logo and re-run to update.")
