from __future__ import annotations

import random
from functools import lru_cache

from PIL import Image, ImageDraw, ImageFilter

from core.models import ENVIRONMENTS

SKY_COLORS = {
    "rooftop": ((10, 17, 35), (49, 48, 69)),
    "sunset_hill": ((23, 31, 65), (226, 105, 76)),
    "bedroom": ((10, 15, 30), (30, 36, 56)),
    "city_street": ((9, 14, 29), (48, 42, 59)),
    "empty_road": ((13, 22, 38), (88, 63, 58)),
    "classroom": ((31, 40, 58), (93, 82, 73)),
    "library": ((18, 24, 37), (61, 51, 45)),
    "rainy_window": ((17, 28, 48), (44, 56, 70)),
    "beach": ((9, 20, 42), (157, 83, 87)),
    "bridge": ((8, 15, 32), (51, 48, 62)),
    "forest": ((8, 22, 27), (48, 58, 48)),
    "stairs": ((22, 28, 39), (73, 72, 74)),
    "hallway": ((20, 26, 39), (71, 66, 64)),
    "transport": ((10, 17, 31), (45, 50, 62)),
    "open_sky": ((8, 17, 42), (31, 43, 69)),
}


def _gradient(size: tuple[int, int], top: tuple[int, int, int], bottom: tuple[int, int, int]) -> Image.Image:
    width, height = size
    image = Image.new("RGB", size)
    pixels = image.load()
    for y in range(height):
        fraction = y / max(1, height - 1)
        color = tuple(round(top[i] * (1 - fraction) + bottom[i] * fraction) for i in range(3))
        for x in range(width):
            pixels[x, y] = color
    return image


def _draw_stars(draw: ImageDraw.ImageDraw, width: int, height: int, seed: int = 19) -> None:
    rng = random.Random(seed)
    for _ in range(max(20, width * height // 20000)):
        x = rng.randrange(width)
        y = rng.randrange(max(1, int(height * 0.55)))
        r = rng.choice((1, 1, 2))
        draw.ellipse((x - r, y - r, x + r, y + r), fill=(195, 205, 224))


def _glow(image: Image.Image, center: tuple[int, int], radius: int, color: tuple[int, int, int]) -> None:
    layer = Image.new("RGBA", image.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    draw.ellipse((center[0] - radius, center[1] - radius, center[0] + radius, center[1] + radius), fill=(*color, 105))
    image.alpha_composite(layer.filter(ImageFilter.GaussianBlur(max(2, radius // 2))))


@lru_cache(maxsize=24)
def render_environment(name: str, width: int, height: int) -> Image.Image:
    """Render a reusable layered backdrop for the built-in environment library."""
    if name not in ENVIRONMENTS:
        raise ValueError(f"Unknown environment: {name}")
    top, bottom = SKY_COLORS[name]
    image = _gradient((width, height), top, bottom).convert("RGBA")
    draw = ImageDraw.Draw(image)
    horizon = int(height * (0.62 if name in ("sunset_hill", "beach", "empty_road") else 0.58))
    _draw_stars(draw, width, height, seed=ENVIRONMENTS.index(name) + 71)

    if name in ("sunset_hill", "beach"):
        sun_y = int(height * 0.40)
        sun_color = (255, 171, 106) if name == "sunset_hill" else (255, 158, 120)
        _glow(image, (width // 2, sun_y), int(width * 0.24), sun_color)
        draw = ImageDraw.Draw(image)
        sun_r = int(width * 0.09)
        draw.ellipse((width // 2 - sun_r, sun_y - sun_r, width // 2 + sun_r, sun_y + sun_r), fill=(255, 194, 129))

    ground_y = horizon
    if name == "sunset_hill":
        draw.polygon([(0, horizon + height * .08), (width * .20, horizon - height * .15), (width * .48, horizon + height * .02), (width * .75, horizon - height * .17), (width, horizon + height * .05), (width, height), (0, height)], fill=(37, 46, 61))
        draw.polygon([(0, horizon + height * .17), (width * .27, horizon - height * .02), (width * .52, horizon + height * .14), (width * .80, horizon - height * .01), (width, horizon + height * .12), (width, height), (0, height)], fill=(24, 40, 47))
        ground_y = int(height * .76)
        draw.polygon([(0, ground_y), (width * .4, ground_y - height * .09), (width * .72, ground_y - height * .02), (width, ground_y - height * .12), (width, height), (0, height)], fill=(19, 38, 35))
        for x in range(0, width, max(22, width // 18)):
            draw.line((x, ground_y + 5, x - 4, ground_y - 10), fill=(54, 68, 51), width=max(1, width // 500))
    elif name in ("city_street", "rooftop", "bridge", "empty_road", "transport"):
        rng = random.Random(12 + ENVIRONMENTS.index(name))
        base = horizon + int(height * .12)
        building_color = (17, 23, 37)
        x = -int(width * .03)
        while x < width:
            bwidth = rng.randint(max(28, width // 12), max(50, width // 6))
            bheight = rng.randint(int(height * .12), int(height * .38))
            draw.rectangle((x, base - bheight, x + bwidth, base), fill=building_color)
            for wx in range(x + 7, x + bwidth - 4, max(10, width // 32)):
                for wy in range(base - bheight + 12, base - 8, max(16, height // 45)):
                    if rng.random() > .36:
                        draw.rectangle((wx, wy, wx + 3, wy + 6), fill=(207, 142, 93, 190))
            x += bwidth - 2
        if name == "rooftop":
            ground_y = int(height * .82)
            draw.rectangle((0, ground_y, width, height), fill=(20, 25, 35))
            draw.line((0, ground_y, width, ground_y), fill=(79, 81, 87), width=max(2, width // 220))
            draw.line((width * .12, ground_y, width * .12, ground_y - height * .11), fill=(70, 76, 84), width=max(2, width // 180))
        elif name == "bridge":
            ground_y = int(height * .79)
            draw.arc((-width * .2, ground_y - height * .2, width * 1.2, ground_y + height * .3), 180, 360, fill=(96, 93, 96), width=max(3, width // 75))
            draw.line((0, ground_y, width, ground_y), fill=(98, 91, 87), width=max(3, width // 60))
            for x in range(0, width, max(20, width // 15)):
                draw.line((x, ground_y, x, ground_y - height * .10), fill=(77, 80, 87), width=max(2, width // 250))
        elif name == "transport":
            ground_y = int(height * .78)
            draw.rounded_rectangle((width * .12, height * .37, width * .89, ground_y), radius=20, fill=(36, 48, 63), outline=(119, 124, 132), width=max(2, width // 250))
            for x in range(int(width * .18), int(width * .84), max(26, width // 7)):
                draw.rectangle((x, height * .42, x + width * .09, height * .56), fill=(179, 143, 111))
            draw.ellipse((width * .22, ground_y - 5, width * .34, ground_y + height * .04), fill=(9, 11, 16))
            draw.ellipse((width * .68, ground_y - 5, width * .80, ground_y + height * .04), fill=(9, 11, 16))
        else:
            ground_y = int(height * .78)
            draw.polygon([(0, ground_y - height * .12), (width * .42, ground_y - height * .04), (width * .58, ground_y - height * .04), (width, ground_y - height * .12), (width, height), (0, height)], fill=(23, 28, 38))
            draw.polygon([(width * .40, ground_y - height * .04), (width * .60, ground_y - height * .04), (width * .84, height), (width * .16, height)], fill=(24, 27, 35))
            draw.line((width * .50, ground_y, width * .50, height), fill=(120, 101, 82), width=max(2, width // 250))
            if name in ("city_street", "empty_road"):
                for x in (width * .18, width * .82):
                    draw.line((x, ground_y, x, ground_y - height * .13), fill=(83, 83, 85), width=max(2, width // 220))
                    draw.ellipse((x - width * .035, ground_y - height * .14, x + width * .035, ground_y - height * .09), fill=(255, 181, 108))
    elif name == "bedroom":
        ground_y = int(height * .80)
        draw.rectangle((width * .12, height * .12, width * .72, height * .48), fill=(17, 27, 45), outline=(111, 101, 95), width=max(3, width // 180))
        for x in (width * .17, width * .40, width * .63):
            draw.rectangle((x, height * .16, x + width * .05, height * .43), fill=(230, 156, 100))
        draw.rectangle((0, ground_y, width, height), fill=(39, 32, 34))
        draw.rectangle((width * .12, height * .58, width * .88, ground_y), fill=(50, 43, 49))
        draw.rectangle((width * .17, height * .54, width * .43, height * .64), fill=(86, 77, 80))
        draw.polygon([(width * .47, height * .62), (width * .85, height * .59), (width * .88, ground_y), (width * .45, ground_y)], fill=(66, 53, 56))
    elif name in ("classroom", "library", "rainy_window", "hallway", "stairs"):
        ground_y = int(height * .82)
        draw.rectangle((0, ground_y, width, height), fill=(37, 34, 36))
        draw.polygon([(0, height * .62), (width, height * .62), (width, height), (0, height)], fill=(47, 42, 43))
        if name == "classroom":
            draw.rectangle((width * .13, height * .20, width * .87, height * .48), fill=(30, 57, 57), outline=(129, 117, 94), width=max(3, width // 170))
            draw.line((width * .14, height * .49, width * .86, height * .49), fill=(117, 95, 73), width=max(5, width // 90))
            for x in (width * .22, width * .48, width * .72):
                draw.polygon([(x, height * .66), (x + width * .21, height * .66), (x + width * .18, height * .70), (x + width * .03, height * .70)], fill=(104, 79, 59))
                draw.line((x + width * .05, height * .70, x + width * .04, height * .82), fill=(58, 49, 43), width=max(3, width // 80))
        elif name == "library":
            for x in (width * .06, width * .38, width * .70):
                draw.rectangle((x, height * .15, x + width * .25, ground_y), fill=(44, 37, 35), outline=(100, 78, 60), width=max(2, width // 220))
                for y in range(int(height * .20), ground_y, max(32, height // 12)):
                    draw.line((x, y, x + width * .25, y), fill=(127, 93, 62), width=max(2, width // 230))
                    for bx in range(int(x + 8), int(x + width * .23), max(12, width // 25)):
                        draw.rectangle((bx, y - height * .06, bx + width * .025, y - 2), fill=random.Random(bx + y).choice([(120, 79, 64), (89, 105, 104), (147, 112, 75)]))
        elif name == "rainy_window":
            draw.rectangle((width * .12, height * .13, width * .88, height * .61), fill=(22, 39, 58), outline=(109, 109, 107), width=max(4, width // 130))
            draw.line((width * .50, height * .14, width * .50, height * .60), fill=(103, 105, 108), width=max(3, width // 180))
            draw.line((width * .13, height * .39, width * .87, height * .39), fill=(103, 105, 108), width=max(3, width // 180))
            rng = random.Random(88)
            for _ in range(width // 5):
                x, y = rng.randrange(width), rng.randrange(int(height * .60))
                draw.line((x, y, x - 5, y + 22), fill=(139, 165, 184, 140), width=max(1, width // 350))
            draw.rectangle((0, height * .61, width, height * .65), fill=(112, 89, 70))
        elif name == "stairs":
            for step in range(12):
                y = height * (0.82 - step * .055)
                x = width * (0.05 + step * .045)
                draw.polygon([(x, y), (width * .96, y - height * .02), (width * .96, y + height * .025), (x, y + height * .055)], fill=(78 + step, 75 + step, 76 + step))
            draw.line((width * .20, height * .48, width * .83, height * .22), fill=(118, 110, 102), width=max(4, width // 90))
        else:
            draw.polygon([(0, height * .24), (width * .46, height * .45), (width * .46, height * .82), (0, height * .82)], fill=(34, 41, 52))
            draw.polygon([(width, height * .24), (width * .54, height * .45), (width * .54, height * .82), (width, height * .82)], fill=(41, 43, 50))
            for y in (height * .38, height * .52, height * .65):
                draw.ellipse((width * .44, y, width * .56, y + height * .05), fill=(240, 165, 99, 110))
    elif name == "forest":
        ground_y = int(height * .77)
        draw.polygon([(0, ground_y), (width * .5, ground_y - height * .14), (width, ground_y), (width, height), (0, height)], fill=(20, 38, 34))
        rng = random.Random(77)
        for x in range(-width // 10, width + width // 10, max(30, width // 8)):
            trunk_w = max(8, width // 35)
            top_y = rng.randint(int(height * .13), int(height * .36))
            draw.polygon([(x, ground_y), (x + trunk_w, ground_y), (x + trunk_w // 2, top_y)], fill=(17, 31, 30))
            draw.polygon([(x - width * .06, top_y + height * .17), (x + trunk_w // 2, top_y - height * .10), (x + width * .07, top_y + height * .17)], fill=(20, 42, 38))
    else:
        ground_y = int(height * .79)
        draw.rectangle((0, ground_y, width, height), fill=(25, 37, 42))
        for offset in range(5):
            y = int(height * (.67 + offset * .035))
            draw.arc((-width * .15, y, width * 1.15, y + height * .12), 0, 180, fill=(111, 122, 129, 170), width=max(2, width // 260))

    # Subtle vignette keeps the bright horizon and dark silhouette in balance.
    vignette = Image.new("RGBA", image.size, (0, 0, 0, 0))
    vignette_draw = ImageDraw.Draw(vignette)
    edge = max(1, width // 18)
    for inset in range(edge):
        alpha = int(52 * (1 - inset / edge))
        vignette_draw.rectangle((inset, inset, width - inset - 1, height - inset - 1), outline=(3, 5, 12, alpha), width=1)
    image.alpha_composite(vignette)
    return image
