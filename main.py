"""
PDF Editor Pro - Editor de PDF con selección, resaltado, eliminación y edición de texto
Mantiene la tipografía original y preserva formularios y estructura del documento.
"""

import sys
import os
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
    app.setApplicationVersion("1.0.0")
    
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
