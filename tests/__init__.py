"""Tests para PDF Editor.

Este directorio contiene los tests automatizados para la aplicación.

Ejecutar tests:
    Tests rápidos (sin pytest):
        cd pdf_editor
        python tests/test_workspace.py
    
    Tests completos con pytest:
        cd pdf_editor
        pip install pytest
        python -m pytest tests/ -v

Cobertura de tests:
    test_workspace.py:
        - TestWorkGroup: Tests para la clase WorkGroup
        - TestWorkspaceManager: Tests para el gestor de workspace
        - TestWorkspaceManagerProcessing: Tests para procesamiento de archivos
        - TestEdgeCases: Tests para casos límite y errores
        - TestConfigPersistence: Tests para persistencia de configuración
"""
