from PIL import Image, ImageDraw, ImageFont
import json
from pathlib import Path
import sys

root, output, *metadata = map(Path, sys.argv[1:])
canvas = Image.new("RGB", (1640, 980), "#101a28")
draw = ImageDraw.Draw(canvas)
font = Path("/usr/share/fonts/truetype/dejavu")

def text(x, y, string, size, color, bold=False):
    face = "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"
    draw.text((x, y), string, fill=color, font=ImageFont.truetype(str(font / face), size))

text(32, 30, "HUMAN3D 2.0  /  M6 COLLISION VALIDATION", 24, "#8fbbd5", True)
title = "Posed shorts with hidden intersections"
if metadata:
    contents = json.loads(metadata[0].read_text())
    title = contents["title"]
text(32, 70, title, 48, "#f4f8fb", True)
panels = [("sampled", "v0.2.0   Sampled clearance", "0 penetration samples"),
          ("triangles", "M6   Triangle intersection", "34 body–garment triangle pairs")]
if metadata:
    panels = contents["panels"]
for i, (file, label, count) in enumerate(panels):
    x, y = 32 + i * 798, 194
    canvas.paste(Image.open(root / (file + ".png")).convert("RGB"), (x, y))
    text(x, 145, label, 28, "#f4f8fb", True)
    text(x, 908, count, 25, "#ff986a" if i else "#bbd9e9", True)
    if i:
        contacts = json.loads((root / "projected-contacts.json").read_text())
        for u, v in contacts:
            cx, cy = x + u * 780, y + (1 - v) * 700
            assert x <= cx < x + 780 and y <= cy < y + 700
            draw.ellipse((cx - 8, cy - 8, cx + 8, cy + 8), fill="#ff8f55", outline="#2b1510", width=2)
        text(x, 944, "Dots mark projected centres of intersecting shell triangles.", 19, "#a8b9ca")
canvas.save(output, optimize=True)
