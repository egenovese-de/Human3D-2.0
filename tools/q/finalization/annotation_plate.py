"""Draw the published face picks and independent joint centers over source renders."""
import argparse
import json
from pathlib import Path

from PIL import Image, ImageDraw


def main(dataset, evidence, output):
    rig = json.loads((evidence / "rig-landmarks.json").read_text())
    face = json.loads((evidence / "face-anchors.json").read_text())
    output.parent.mkdir(parents=True, exist_ok=True)
    plate = Image.new("RGB", (4 * 288, 384), "#f5f5f5")
    draw = ImageDraw.Draw(plate)
    for i, (identity, yaw) in enumerate((("f_af01", 0), ("f_af01", 90), ("m_la01", 0), ("m_la01", 90))):
        render = Image.open(dataset / f"{identity}_neutral" / f"yaw-{yaw}.png").convert("RGBA")
        canvas = Image.new("RGBA", render.size, "#ededed")
        canvas.alpha_composite(render)
        panel = canvas.resize((288, 288)).convert("RGB")
        points = next(row for row in rig if row["fixture"] == f"{identity}_neutral")
        anchors = next(view["anchors"] for view in points["views"] if view["yaw_deg"] == yaw)
        points_draw = ImageDraw.Draw(panel)
        for anchor in anchors:
            x, y = (coordinate * .75 for coordinate in anchor["xy_px"])
            points_draw.ellipse((x-3, y-3, x+3, y+3), fill="#0ddcc2", outline="#133e3b")
        x = i * 288
        plate.paste(panel, (x, 30))
        draw.text((x+12, 11), f"{identity}   yaw {yaw} deg", fill="#172323")
        head = canvas.crop((150, 25, 220, 92)).resize((68, 65)).convert("RGB")
        head_draw = ImageDraw.Draw(head)
        for row in face:
            if row["identity"] == identity and row["yaw_deg"] == yaw and row["xyz_m"] is not None:
                u, v = row["xy_px"]
                u, v = (u-150)*68/70, (v-25)*65/67
                head_draw.ellipse((u-1, v-1, u+1, v+1), fill="#ffd829")
        plate.paste(head, (x+206, 310))
    draw.text((12, 326), "Cyan  Independent joint centers", fill="#133e3b")
    draw.text((12, 344), "Yellow  First-hit facial picks", fill="#514300")
    plate.save(output, optimize=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    for argument in ("dataset", "evidence", "output"):
        parser.add_argument(argument, type=Path)
    main(**vars(parser.parse_args()))
