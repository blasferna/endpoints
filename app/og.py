import os
from tempfile import TemporaryFile
import zipfile
from io import BytesIO

import requests
from PIL import Image, ImageDraw, ImageFont

FONT_CACHE_DIR = "./font_cache/"


def create_gradient(width, height, top_color, bottom_color):
    base = Image.new("RGB", (width, height), top_color)
    top = Image.new("RGB", (width, height), bottom_color)
    mask = Image.new("L", (width, height))
    mask_data = []
    for y in range(height):
        mask_data.extend([int(255 * (y / height))] * width)
    mask.putdata(mask_data)
    base.paste(top, (0, 0), mask)
    return base


def download_font(font_name: str):
    font_directory = FONT_CACHE_DIR

    if not os.path.isdir(font_directory):
        url = f"https://fonts.google.com/download?family={font_name}"
        response = requests.get(url, stream=True)

        tmp = TemporaryFile()
        for chunk in response.iter_content(chunk_size=32768):
            tmp.write(chunk)

        zip = zipfile.ZipFile(tmp)
        files = [
            file
            for file in zip.namelist()
            if file.endswith(".ttf") or file.endswith(".otf")
        ]
        zip.extractall(FONT_CACHE_DIR, files)

        tmp.close()


def get_image(name, thumbnail: tuple = None, opacity=1):
    with open(f"app/resources/img/{name}.png", "rb") as f:
        image_bytes = f.read()

    image_stream = BytesIO(image_bytes)
    image = Image.open(image_stream)
    if thumbnail:
        image.thumbnail(thumbnail)
    rgba = image.convert("RGBA")

    if opacity != 1 and opacity <= 1 and opacity >= 0:
        for x in range(rgba.width):
            for y in range(rgba.height):
                r, g, b, a = rgba.getpixel((x, y))
                rgba.putpixel((x, y), (r, g, b, int(a * opacity)))

    return rgba


def wrap_text(text, width, font):
    lines = []
    if font.getsize(text)[0] <= width:
        lines.append(text)
    else:
        words = text.split(" ")
        i = 0
        while i < len(words):
            line = ""
            while i < len(words) and font.getsize(line + words[i])[0] <= width:
                line = line + words[i] + " "
                i += 1
            if not line:
                line = words[i]
                i += 1
            lines.append(line)
    return lines


def generate_og_image(
    title: str,
    site_name: str,
    top_color: tuple = (206, 236, 255),
    bottom_color: tuple = (236, 248, 255),
    font_name: str = "Roboto",
    tag: str = None,
):
    download_font(font_name)

    img_width, img_height = 1200, 630 

    img = create_gradient(img_width, img_height, top_color, bottom_color).convert(
        "RGBA"
    )
    d = ImageDraw.Draw(img)

    title_font = ImageFont.truetype(FONT_CACHE_DIR + font_name + "-Medium.ttf", 70)
    site_font = ImageFont.truetype(FONT_CACHE_DIR + font_name + "-Regular.ttf", 30)

    code_logo = get_image("code", (120, 120))
    img.paste(code_logo, (45, 50), code_logo)

    title_lines = wrap_text(title, 0.8 * img_width - 2 * 50, title_font)
    title_y = 200 

    line_spacing = 10

    for line in title_lines:
        d.text((50, title_y), line, fill="#252525", font=title_font)
        title_y += title_font.getsize("A")[1] + line_spacing

    site_x = 50
    site_y = img_height - site_font.getsize("A")[1] - 50

    d.text((site_x, site_y), site_name, fill="#585858", font=site_font)

    if tag:
        try:
            tag_image = get_image(tag, opacity=0.5)
            img.paste(tag_image, (894, 324), tag_image)
        except FileNotFoundError:
            pass

    img_file = BytesIO()
    img.save(img_file, "png")
    img_file.seek(0)
    return img_file
