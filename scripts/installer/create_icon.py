"""
Genera un icono básico para la aplicación usando PIL
Ejecutar: python create_icon.py
"""
import os

def create_icon():
    """Crea un icono básico para PDF Editor"""
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        print("Instalando Pillow...")
        os.system("pip install Pillow")
        from PIL import Image, ImageDraw, ImageFont
    
    # Crear imagen de 256x256
    size = 256
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # Fondo redondeado (rojo/naranja)
    margin = 10
    draw.rounded_rectangle(
        [margin, margin, size - margin, size - margin],
        radius=40,
        fill=(220, 53, 69)  # Rojo
    )
    
    # Dibujar símbolo de PDF
    # Documento blanco
    doc_margin = 50
    doc_width = size - 2 * doc_margin
    doc_height = int(doc_width * 1.3)
    doc_top = (size - doc_height) // 2
    
    # Sombra
    draw.rounded_rectangle(
        [doc_margin + 5, doc_top + 5, doc_margin + doc_width + 5, doc_top + doc_height + 5],
        radius=10,
        fill=(150, 30, 40)
    )
    
    # Documento
    draw.rounded_rectangle(
        [doc_margin, doc_top, doc_margin + doc_width, doc_top + doc_height],
        radius=10,
        fill=(255, 255, 255)
    )
    
    # Líneas de texto
    line_margin = 20
    line_y = doc_top + 40
    line_height = 15
    line_spacing = 25
    
    for i in range(5):
        width = doc_width - 2 * line_margin - (20 if i == 4 else 0)
        draw.rounded_rectangle(
            [doc_margin + line_margin, line_y + i * line_spacing,
             doc_margin + line_margin + width, line_y + i * line_spacing + line_height],
            radius=3,
            fill=(200, 200, 200)
        )
    
    # Texto "PDF"
    try:
        font = ImageFont.truetype("arial.ttf", 36)
    except:
        font = ImageFont.load_default()
    
    text = "PDF"
    bbox = draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    text_x = (size - text_width) // 2
    text_y = doc_top + doc_height - 50
    
    draw.text((text_x, text_y), text, fill=(220, 53, 69), font=font)
    
    # Guardar en diferentes tamaños para ICO
    icon_sizes = [(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
    
    # Guardar PNG grande
    output_dir = os.path.dirname(os.path.abspath(__file__))
    png_path = os.path.join(output_dir, "app_icon.png")
    img.save(png_path, "PNG")
    print(f"[OK] PNG guardado: {png_path}")
    
    # Guardar ICO (Windows)
    ico_path = os.path.join(output_dir, "app_icon.ico")
    img.save(ico_path, format='ICO', sizes=icon_sizes)
    print(f"[OK] ICO guardado: {ico_path}")
    
    # Guardar ICNS (macOS) - Necesita iconutil en Mac, hacemos PNG por ahora
    icns_png = os.path.join(output_dir, "app_icon_mac.png")
    img.save(icns_png, "PNG")
    print(f"[OK] PNG para Mac guardado: {icns_png}")
    
    print("")
    print("[SUCCESS] Iconos generados correctamente!")
    print("")
    print("Para macOS, convierte app_icon_mac.png a .icns usando:")
    print("  1. En Mac: iconutil -c icns icon.iconset")
    print("  2. O usa una herramienta online de conversion PNG a ICNS")

if __name__ == "__main__":
    create_icon()
