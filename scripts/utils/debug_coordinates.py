"""
Script de diagnóstico para entender el sistema de coordenadas del PDF.
Ejecuta esto con un PDF para ver exactamente cómo están estructuradas las coordenadas.
"""
import fitz
import sys

def analyze_pdf(pdf_path):
    """Analiza las coordenadas y transformaciones de un PDF."""
    doc = fitz.open(pdf_path)
    
    print("=" * 60)
    print(f"ANÁLISIS DE PDF: {pdf_path}")
    print("=" * 60)
    
    for page_num in range(min(2, doc.page_count)):  # Solo las primeras 2 páginas
        page = doc[page_num]
        
        print(f"\n--- PÁGINA {page_num + 1} ---")
        print(f"page.rect (área visual): {page.rect}")
        print(f"page.rect.width x height: {page.rect.width:.1f} x {page.rect.height:.1f}")
        print(f"page.mediabox: {page.mediabox}")
        print(f"page.cropbox: {page.cropbox}")
        print(f"page.rotation: {page.rotation}°")
        print(f"page.transformation_matrix: {page.transformation_matrix}")
        print(f"page.derotation_matrix: {page.derotation_matrix}")
        
        # Renderizar con zoom 1.0
        mat = fitz.Matrix(1.0, 1.0)
        pix = page.get_pixmap(matrix=mat, alpha=False)
        print(f"\nPixmap (zoom=1.0):")
        print(f"  Tamaño: {pix.width} x {pix.height}")
        
        # Verificar si hay imágenes
        images = page.get_images()
        print(f"\nImágenes en la página: {len(images)}")
        for idx, img in enumerate(images):
            xref = img[0]
            print(f"  Imagen {idx}: xref={xref}, size={img[2]}x{img[3]}")
        
        # Verificar texto
        text = page.get_text("text")
        has_text = bool(text.strip())
        print(f"\n¿Tiene texto extraíble?: {has_text}")
        if has_text:
            print(f"  Muestra: {text[:100]}...")
        
        # Probar añadir una anotación de prueba en coordenadas conocidas
        # Esto es solo para diagnóstico
        print("\n--- PRUEBA DE COORDENADAS ---")
        
        # Punto superior izquierdo de la página visual
        print(f"Esquina superior izquierda de page.rect: ({page.rect.x0}, {page.rect.y0})")
        print(f"Esquina inferior derecha de page.rect: ({page.rect.x1}, {page.rect.y1})")
        
        # La matriz de transformación nos dice cómo convertir
        # coordenadas "visuales" a coordenadas "internas" del PDF
        print(f"\nPara convertir coordenadas visuales a internas:")
        print(f"  Si rotation=0: coordenadas son directas")
        print(f"  Si rotation=90: x_interno = y_visual, y_interno = width - x_visual")
        print(f"  Si rotation=180: x_interno = width - x_visual, y_interno = height - y_visual")
        print(f"  Si rotation=270: x_interno = height - y_visual, y_interno = x_visual")
        
        # Verificar la relación entre mediabox y rect
        if page.rotation != 0:
            print(f"\n⚠️ PÁGINA ROTADA {page.rotation}°")
            print(f"  El pixmap muestra la página rotada visualmente")
            print(f"  Pero las anotaciones usan coordenadas del mediabox original")
            print(f"  MediaBox: {page.mediabox.width:.1f} x {page.mediabox.height:.1f}")
            print(f"  Rect (visual): {page.rect.width:.1f} x {page.rect.height:.1f}")
    
    doc.close()
    print("\n" + "=" * 60)

if __name__ == "__main__":
    if len(sys.argv) > 1:
        analyze_pdf(sys.argv[1])
    else:
        print("Uso: python debug_coordinates.py <archivo.pdf>")
        print("\nArrastra un PDF a la terminal o proporciona la ruta.")
