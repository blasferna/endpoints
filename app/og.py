import requests
import os
import tempfile
import zipfile
from PIL import Image, ImageDraw, ImageFont
import cairosvg

# Define el directorio de caché para las fuentes
FONT_CACHE_DIR = "./font_cache/"


def create_gradient(width, height, top_color, bottom_color):
    base = Image.new('RGB', (width, height), top_color)
    top = Image.new('RGB', (width, height), bottom_color)
    mask = Image.new('L', (width, height))
    mask_data = []
    for y in range(height):
        mask_data.extend([int(255 * (y / height))] * width)
    mask.putdata(mask_data)
    base.paste(top, (0, 0), mask)
    return base


def download_font(font_name: str):
    os.makedirs(FONT_CACHE_DIR, exist_ok=True)

    font_path = FONT_CACHE_DIR + font_name

    if not os.path.isfile(font_path):
        url = f"https://fonts.google.com/download?family={font_name}"
        response = requests.get(url)
        
        tmp = tempfile.NamedTemporaryFile(delete=False)
        tmp.write(response.content)
        tmp.close()

        with zipfile.ZipFile(tmp.name, 'r') as zip_ref:
            for file in zip_ref.namelist():
                if file.endswith(".ttf") or file.endswith(".otf"):
                    zip_ref.extract(file, FONT_CACHE_DIR)
                    os.rename(FONT_CACHE_DIR + file, font_path)
                    break

        os.remove(tmp.name)

    return font_path

def wrap_text(text, width, font):
    lines = []
    if font.getsize(text)[0] <= width:
        lines.append(text)
    else:
        words = text.split(' ')
        i = 0
        while i < len(words):
            line = ''
            while i < len(words) and font.getsize(line + words[i])[0] <= width:
                line = line + words[i] + " "
                i += 1
            if not line:
                line = words[i]
                i += 1
            lines.append(line)
    return lines

def generate_og_image(title: str, site_name: str, top_color: tuple, bottom_color: tuple, 
                      font_name: str, svg_path: str, output_path: str):
    # Descarga la fuente y obtén la ruta del archivo
    font_path = download_font(font_name)
    
    # Define el tamaño de la imagen
    img_width, img_height = 1200, 630  # Tamaño estándar para las imágenes Open Graph

    # Create the gradient background
    img = create_gradient(img_width, img_height, top_color, bottom_color)
    
    # Crea un objeto ImageDraw
    d = ImageDraw.Draw(img)

    # Define las fuentes
    title_font = ImageFont.truetype(font_path, 60)
    site_font = ImageFont.truetype(font_path, 30)

    # Dibuja el título y el nombre del sitio en la imagen
    title_lines = wrap_text(title, 0.8 * img_width - 2*50, title_font)
    title_y = 50  # Start at top padding for title

    for line in title_lines:
        d.text((50, title_y), line, fill=(0, 0, 0), font=title_font)
        title_y += title_font.getsize('A')[1]

    # Position the icon and site name at the bottom left with 50px padding
    cairosvg.svg2png(url=svg_path, write_to='temp.png')
    icon = Image.open('temp.png')
    icon.thumbnail((50, 50))

    site_x = 50
    site_y = img_height - site_font.getsize('A')[1] - 50

    img.paste(icon, (site_x, site_y))

    site_x += icon.width + 10
    d.text((site_x, site_y), site_name, fill="#000000", font=site_font)

    # Guarda la imagen
    img.save(output_path)

# Llamada a la función con los parámetros requeridos
generate_og_image('Este es uno de lo mejores ejemplo de que podemos lograr algo grando con muy poco', 'blasferna.com', 
                  (146, 151, 255), (222, 224, 252), 'Roboto', 'world_icon.svg', 'og_image.png')
