from __future__ import annotations

import io
import re
from typing import Tuple

from PIL import Image, ImageDraw, ImageFont

HEX_REGEX = re.compile(r"^#?([0-9a-fA-F]{6})$")


def normalize_hex(hex_input: str) -> str:
    match = HEX_REGEX.match(hex_input.strip())
    if not match:
        raise ValueError("Invalid HEX color. Use format #RRGGBB or RRGGBB.")
    return f"#{match.group(1).upper()}"


def hex_to_rgb(hex_color: str) -> Tuple[int, int, int]:
    hex_color = normalize_hex(hex_color)
    hex_part = hex_color.lstrip("#")
    return tuple(int(hex_part[i:i+2], 16) for i in (0, 2, 4))  # type: ignore


def generate_swatch_image(hex_color: str, orientation: str, text_overlay: bool = True) -> Image.Image:
    orientation = (orientation or "Square").lower()

    if orientation == "portrait":
        width, height = 1080, 1350
    elif orientation == "landscape":
        width, height = 1350, 1080
    else:
        width, height = 1080, 1080

    rgb = hex_to_rgb(hex_color)

    image = Image.new("RGB", (width, height), rgb)

    # Optional border
    border = max(4, width // 200)
    draw = ImageDraw.Draw(image)
    draw.rectangle([(0, 0), (width - 1, height - 1)], outline=(255, 255, 255), width=border)

    if text_overlay:
        # Draw centered HEX text with shadow for readability
        label = normalize_hex(hex_color)
        try:
            font = ImageFont.truetype("DejaVuSans.ttf", size=max(24, width // 18))
        except Exception:
            font = ImageFont.load_default()
        text_w, text_h = draw.textlength(label, font=font), font.size
        x = (width - text_w) / 2
        y = (height - text_h) / 2
        shadow_color = (0, 0, 0)
        for dx, dy in [(-2, -2), (2, -2), (-2, 2), (2, 2)]:
            draw.text((x + dx, y + dy), label, font=font, fill=shadow_color)
        draw.text((x, y), label, font=font, fill=(255, 255, 255))

    return image


def image_to_bytes(image: Image.Image, export_format: str) -> bytes:
    export_format = (export_format or "JPG").upper()
    buf = io.BytesIO()
    if export_format == "PNG":
        image.save(buf, format="PNG", optimize=True)
    else:
        image.save(buf, format="JPEG", quality=95, optimize=True)
    return buf.getvalue()