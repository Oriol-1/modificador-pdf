"""
PDF Editor Pro - Editor de PDF con selección, resaltado, eliminación y edición de texto
Mantiene la tipografía original y preserva formularios y estructura del documento.
"""

import sys
import os
import faulthandler

# Habilitar faulthandler: si ocurre un segfault o crash de C (PyMuPDF, PyQt),
# imprime un traceback Python apuntando a la linea exacta antes de morir.
# Asi podemos diagnosticar crashes nativos en lugar de quedarnos a ciegas.
try:
    faulthandler.enable()
except Exception:
    pass

# Hook de excepciones globales: captura cualquier excepcion no controlada
# que escape al event loop de Qt. Sin esto, una excepcion no atrapada
# puede provocar que Qt aborte el proceso silenciosamente. Imprimimos el
# traceback completo para poder diagnosticar.
def _excepthook(exc_type, exc_value, exc_tb):
    import traceback
    try:
        sys.stderr.write("\n=== UNHANDLED EXCEPTION ===\n")
        traceback.print_exception(exc_type, exc_value, exc_tb)
        sys.stderr.write("=== END EXCEPTION ===\n")
        sys.stderr.flush()
    except Exception:
        pass
    # Mantener comportamiento por defecto tambien
    sys.__excepthook__(exc_type, exc_value, exc_tb)

sys.excepthook = _excepthook

# Reconfigurar stdout/stderr a UTF-8 con errors='replace' para que ningún
# print con caracteres no codificables en la consola Windows (cp1252) pueda
# tumbar la app — históricamente caracteres como ✓, ⚠, 📁 dentro de logs de
# debug provocaban UnicodeEncodeError abortando flujos críticos como guardar.
try:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt
from ui.main_window import MainWindow


def main():
    """Punto de entrada principal de la aplicación."""
    # Configurar alta resolución DPI
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    
    app = QApplication(sys.argv)
    app.setApplicationName("PDF Editor Pro")
    app.setOrganizationName("PDF Editor")
    app.setApplicationVersion("2.1.5")
    
    # Aplicar estilo
    app.setStyle('Fusion')
    
    window = MainWindow()
    window.show()
    
    # Si se pasó un archivo como argumento, abrirlo
    if len(sys.argv) > 1:
        pdf_path = sys.argv[1]
        if os.path.exists(pdf_path):
            window.load_pdf(pdf_path)
    
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
