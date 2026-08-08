from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw


def create_icon() -> None:
    assets = Path(__file__).resolve().parents[1] / "assets"
    assets.mkdir(parents=True, exist_ok=True)
    size = 512
    image = Image.new("RGBA", (size, size), (22, 25, 29, 255))
    draw = ImageDraw.Draw(image)

    for radius in range(220, 62, -1):
        t = (220 - radius) / 158
        color = (
            round(47 + 20 * t),
            round(126 + 88 * t),
            round(184 + 45 * t),
            255,
        )
        bounds = (size // 2 - radius, size // 2 - radius, size // 2 + radius, size // 2 + radius)
        draw.ellipse(bounds, outline=color, width=4)

    blades = [
        [(256, 84), (348, 238), (288, 254), (214, 154)],
        [(428, 190), (288, 254), (306, 314), (406, 272)],
        [(376, 394), (306, 314), (250, 348), (294, 430)],
        [(190, 428), (250, 348), (204, 306), (104, 338)],
        [(84, 274), (204, 306), (218, 244), (116, 190)],
        [(154, 104), (218, 244), (278, 222), (256, 84)],
    ]
    blade_colors = ["#65c6e8", "#479adb", "#596fd0", "#8064c7", "#3a88bd", "#58b9d4"]
    for points, color in zip(blades, blade_colors):
        draw.polygon(points, fill=color)
    draw.ellipse((207, 207, 305, 305), fill="#171a1e", outline="#d9f3ff", width=7)
    draw.ellipse((232, 232, 280, 280), fill="#3d95c8")

    png_path = assets / "app.png"
    ico_path = assets / "app.ico"
    image.save(png_path, format="PNG")
    image.save(ico_path, format="ICO", sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
    print(f"Created {png_path} and {ico_path}")


if __name__ == "__main__":
    create_icon()

