"""
Tests para el sistema de Workspace del PDF Editor.
Ejecutar con: python -m pytest tests/test_workspace.py -v
O sin pytest: python tests/test_workspace.py
"""

import os
import sys
import tempfile
import shutil
from datetime import datetime

# Intentar importar pytest (opcional - no requerido para tests básicos)
try:
    import pytest  # type: ignore
    PYTEST_AVAILABLE = True
except ImportError:
    PYTEST_AVAILABLE = False

# Agregar el directorio padre al path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ui.workspace_manager import WorkGroup, WorkspaceManager


class TestWorkGroup:
    """Tests para la clase WorkGroup."""
    
    def setup_method(self):
        """Configuración antes de cada test."""
        self.temp_dir = tempfile.mkdtemp()
        self.group_path = os.path.join(self.temp_dir, "TestGroup")
        os.makedirs(self.group_path)
        # Crear subcarpetas como lo haría el WorkspaceManager
        os.makedirs(os.path.join(self.group_path, "Origen"))
        os.makedirs(os.path.join(self.group_path, "Modificado - Sí"))
        os.makedirs(os.path.join(self.group_path, "Modificado - No"))
        
    def teardown_method(self):
        """Limpieza después de cada test."""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_workgroup_creation(self):
        """Test: Crear un WorkGroup correctamente."""
        group = WorkGroup(self.group_path)
        
        assert group.name == "TestGroup"
        assert group.path == self.group_path
        assert os.path.exists(group.origin_folder)
        assert os.path.exists(group.modified_folder)
        assert os.path.exists(group.original_folder)
    
    def test_workgroup_folder_names(self):
        """Test: Los nombres de carpetas son correctos."""
        group = WorkGroup(self.group_path)
        
        assert "Origen" in group.origin_folder
        assert "Modificado - Sí" in group.modified_folder
        assert "Modificado - No" in group.original_folder
    
    def test_workgroup_stats_empty(self):
        """Test: Estadísticas de grupo vacío."""
        group = WorkGroup(self.group_path)
        
        assert group.get_pending_count() == 0
        assert group.get_modified_count() == 0
        assert group.get_archived_count() == 0
        assert group.is_complete() == True  # Sin pendientes = completo
    
    def test_workgroup_stats_with_files(self):
        """Test: Estadísticas con archivos."""
        group = WorkGroup(self.group_path)
        
        # Crear archivos de prueba
        with open(os.path.join(group.origin_folder, "test1.pdf"), 'w') as f:
            f.write("fake pdf 1")
        with open(os.path.join(group.origin_folder, "test2.pdf"), 'w') as f:
            f.write("fake pdf 2")
        with open(os.path.join(group.modified_folder, "test3.pdf"), 'w') as f:
            f.write("fake pdf 3")
        
        assert group.get_pending_count() == 2
        assert group.get_modified_count() == 1
        assert group.is_complete() == False
    
    def test_workgroup_get_pending_pdfs(self):
        """Test: Obtener lista de PDFs pendientes."""
        group = WorkGroup(self.group_path)
        
        # Crear archivos de prueba
        pdf1 = os.path.join(group.origin_folder, "001_test1.pdf")
        pdf2 = os.path.join(group.origin_folder, "002_test2.pdf")
        
        with open(pdf1, 'w') as f:
            f.write("fake pdf 1")
        with open(pdf2, 'w') as f:
            f.write("fake pdf 2")
        
        pending = group.get_pending_pdfs()
        
        assert len(pending) == 2
        assert pdf1 in pending
        assert pdf2 in pending
    
    def test_workgroup_to_dict(self):
        """Test: Serializar WorkGroup a diccionario."""
        group = WorkGroup(self.group_path)
        
        data = group.to_dict()
        
        assert data['name'] == "TestGroup"
        assert data['path'] == self.group_path
        assert 'created_at' in data
    
    def test_workgroup_from_dict(self):
        """Test: Deserializar WorkGroup desde diccionario."""
        data = {
            'name': "TestGroup",
            'path': self.group_path,
            'created_at': datetime.now().isoformat()
        }
        
        group = WorkGroup.from_dict(data)
        
        assert group.name == "TestGroup"
        assert group.path == self.group_path


class TestWorkspaceManager:
    """Tests para la clase WorkspaceManager."""
    
    def setup_method(self):
        """Configuración antes de cada test."""
        self.temp_dir = tempfile.mkdtemp()
        self.manager = WorkspaceManager()
        # Limpiar estado anterior
        self.manager.base_path = None
        self.manager.work_groups = []
        self.manager.current_group = None
        
    def teardown_method(self):
        """Limpieza después de cada test."""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_set_base_path(self):
        """Test: Establecer carpeta base."""
        result = self.manager.set_base_path(self.temp_dir)
        
        assert result == True
        assert self.manager.base_path == self.temp_dir
        assert self.manager.is_workspace_active() == True
    
    def test_set_base_path_invalid(self):
        """Test: Establecer carpeta base inválida."""
        result = self.manager.set_base_path("/ruta/que/no/existe")
        
        assert result == False
    
    def test_create_new_group_without_base_path(self):
        """Test: Crear grupo sin carpeta base configurada."""
        pdf_files = ["/fake/path/test.pdf"]
        
        group = self.manager.create_new_group(pdf_files)
        
        assert group is None
    
    def test_create_new_group(self):
        """Test: Crear nuevo grupo de trabajo."""
        self.manager.set_base_path(self.temp_dir)
        
        # Crear PDFs de prueba
        pdf1 = os.path.join(self.temp_dir, "test1.pdf")
        pdf2 = os.path.join(self.temp_dir, "test2.pdf")
        
        with open(pdf1, 'w') as f:
            f.write("fake pdf 1")
        with open(pdf2, 'w') as f:
            f.write("fake pdf 2")
        
        group = self.manager.create_new_group([pdf1, pdf2])
        
        assert group is not None
        assert "Grupo_" in group.name
        assert "2pdfs" in group.name
        assert group.get_pending_count() == 2
        assert self.manager.current_group == group
    
    def test_create_group_name_format(self):
        """Test: Formato del nombre del grupo."""
        self.manager.set_base_path(self.temp_dir)
        
        pdf1 = os.path.join(self.temp_dir, "test.pdf")
        with open(pdf1, 'w') as f:
            f.write("fake pdf")
        
        group = self.manager.create_new_group([pdf1])
        
        # Formato: Grupo_YYYY-MM-DD_HHMMSS_Xpdfs
        parts = group.name.split("_")
        assert parts[0] == "Grupo"
        assert len(parts) >= 3
        assert "pdf" in parts[-1].lower()
    
    def test_file_ordering_prefix(self):
        """Test: Los archivos tienen prefijo de orden."""
        self.manager.set_base_path(self.temp_dir)
        
        # Crear PDFs de prueba
        pdfs = []
        for i in range(3):
            pdf = os.path.join(self.temp_dir, f"archivo_{i}.pdf")
            with open(pdf, 'w') as f:
                f.write(f"fake pdf {i}")
            pdfs.append(pdf)
        
        group = self.manager.create_new_group(pdfs)
        pending = group.get_pending_pdfs()
        
        # Verificar que tienen prefijos 001_, 002_, 003_
        for i, pdf_path in enumerate(sorted(pending)):
            filename = os.path.basename(pdf_path)
            expected_prefix = f"{i+1:03d}_"
            assert filename.startswith(expected_prefix), f"Archivo {filename} debería empezar con {expected_prefix}"
    
    def test_is_file_in_origin(self):
        """Test: Detectar archivo en carpeta Origen."""
        self.manager.set_base_path(self.temp_dir)
        
        pdf = os.path.join(self.temp_dir, "test.pdf")
        with open(pdf, 'w') as f:
            f.write("fake pdf")
        
        group = self.manager.create_new_group([pdf])
        
        # Obtener un archivo del origen
        pending = group.get_pending_pdfs()
        assert len(pending) > 0
        
        assert self.manager.is_file_in_origin(pending[0]) == True
        assert self.manager.is_file_in_origin("/otra/ruta/test.pdf") == False
    
    def test_get_stats(self):
        """Test: Obtener estadísticas globales."""
        self.manager.set_base_path(self.temp_dir)
        
        # Crear grupo con archivos
        pdf1 = os.path.join(self.temp_dir, "test1.pdf")
        pdf2 = os.path.join(self.temp_dir, "test2.pdf")
        
        with open(pdf1, 'w') as f:
            f.write("fake pdf 1")
        with open(pdf2, 'w') as f:
            f.write("fake pdf 2")
        
        self.manager.create_new_group([pdf1, pdf2])
        
        stats = self.manager.get_stats()
        
        assert stats['total_groups'] == 1
        assert stats['pending'] == 2
        assert stats['modified'] == 0
        assert stats['backups'] == 0
    
    def test_multiple_groups(self):
        """Test: Crear múltiples grupos independientes."""
        self.manager.set_base_path(self.temp_dir)
        
        # Grupo 1
        pdf1 = os.path.join(self.temp_dir, "test1.pdf")
        with open(pdf1, 'w') as f:
            f.write("fake pdf 1")
        group1 = self.manager.create_new_group([pdf1])
        
        # Grupo 2
        pdf2 = os.path.join(self.temp_dir, "test2.pdf")
        with open(pdf2, 'w') as f:
            f.write("fake pdf 2")
        group2 = self.manager.create_new_group([pdf2])
        
        assert len(self.manager.work_groups) == 2
        assert group1.path != group2.path
        assert group1.name != group2.name
    
    def test_get_pending_pdfs_all_groups(self):
        """Test: Obtener todos los PDFs pendientes de todos los grupos."""
        self.manager.set_base_path(self.temp_dir)
        
        # Grupo 1
        pdf1 = os.path.join(self.temp_dir, "test1.pdf")
        with open(pdf1, 'w') as f:
            f.write("fake pdf 1")
        self.manager.create_new_group([pdf1])
        
        # Grupo 2
        pdf2 = os.path.join(self.temp_dir, "test2.pdf")
        with open(pdf2, 'w') as f:
            f.write("fake pdf 2")
        self.manager.create_new_group([pdf2])
        
        all_pending = self.manager.get_pending_pdfs()
        
        assert len(all_pending) == 2


class TestWorkspaceManagerProcessing:
    """Tests para el procesamiento de archivos guardados."""
    
    def setup_method(self):
        """Configuración antes de cada test."""
        self.temp_dir = tempfile.mkdtemp()
        self.manager = WorkspaceManager()
        self.manager.base_path = None
        self.manager.work_groups = []
        self.manager.current_group = None
        self.manager.set_base_path(self.temp_dir)
        
    def teardown_method(self):
        """Limpieza después de cada test."""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_process_saved_pdf(self):
        """Test: Procesar PDF guardado mueve a carpetas correctas."""
        # Crear grupo con un PDF
        pdf = os.path.join(self.temp_dir, "original.pdf")
        with open(pdf, 'w') as f:
            f.write("contenido original")
        
        group = self.manager.create_new_group([pdf])
        pending = group.get_pending_pdfs()
        original_path = pending[0]
        
        # Simular contenido modificado
        modified_content = b"contenido modificado"
        
        # Procesar
        result = self.manager.process_saved_pdf(original_path, modified_content)
        
        assert result is not None
        assert result['modified'] is not None
        assert os.path.exists(result['modified'])
        assert "Modificado - Sí" in result['modified']
    
    def test_find_group_for_file(self):
        """Test: Encontrar grupo al que pertenece un archivo."""
        pdf = os.path.join(self.temp_dir, "test.pdf")
        with open(pdf, 'w') as f:
            f.write("fake pdf")
        
        group = self.manager.create_new_group([pdf])
        pending = group.get_pending_pdfs()
        
        found_group = self.manager.find_group_for_file(pending[0])
        
        assert found_group is not None
        assert found_group.path == group.path


class TestEdgeCases:
    """Tests para casos límite y errores."""
    
    def setup_method(self):
        """Configuración antes de cada test."""
        self.temp_dir = tempfile.mkdtemp()
        self.manager = WorkspaceManager()
        self.manager.base_path = None
        self.manager.work_groups = []
        self.manager.current_group = None
        
    def teardown_method(self):
        """Limpieza después de cada test."""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_create_group_with_nonexistent_pdf(self):
        """Test: Crear grupo con PDF que no existe."""
        self.manager.set_base_path(self.temp_dir)
        
        group = self.manager.create_new_group(["/no/existe/test.pdf"])
        
        # Debería crear el grupo pero sin archivos
        assert group is not None
        assert group.get_pending_count() == 0
    
    def test_create_group_empty_list(self):
        """Test: Crear grupo con lista vacía."""
        self.manager.set_base_path(self.temp_dir)
        
        group = self.manager.create_new_group([])
        
        # No debería crear grupo con lista vacía
        assert group is None
    
    def test_special_characters_in_filename(self):
        """Test: Manejar caracteres especiales en nombres de archivo."""
        self.manager.set_base_path(self.temp_dir)
        
        # Crear PDF con nombre especial (sin caracteres prohibidos en Windows)
        pdf = os.path.join(self.temp_dir, "archivo con espacios y (parentesis).pdf")
        with open(pdf, 'w') as f:
            f.write("fake pdf")
        
        group = self.manager.create_new_group([pdf])
        
        assert group is not None
        assert group.get_pending_count() == 1
    
    def test_duplicate_filenames(self):
        """Test: Manejar nombres de archivo duplicados."""
        self.manager.set_base_path(self.temp_dir)
        
        # Crear dos carpetas con PDFs del mismo nombre
        dir1 = os.path.join(self.temp_dir, "dir1")
        dir2 = os.path.join(self.temp_dir, "dir2")
        os.makedirs(dir1)
        os.makedirs(dir2)
        
        pdf1 = os.path.join(dir1, "test.pdf")
        pdf2 = os.path.join(dir2, "test.pdf")
        
        with open(pdf1, 'w') as f:
            f.write("contenido 1")
        with open(pdf2, 'w') as f:
            f.write("contenido 2")
        
        group = self.manager.create_new_group([pdf1, pdf2])
        
        # Debería manejar duplicados (posiblemente renombrando)
        assert group is not None
        # Al menos uno debería estar en el grupo
        assert group.get_pending_count() >= 1
    
    def test_very_long_filename(self):
        """Test: Manejar nombres de archivo muy largos."""
        self.manager.set_base_path(self.temp_dir)
        
        # Windows tiene límite de ~260 caracteres en la ruta completa
        # Crear nombre largo pero válido
        long_name = "a" * 100 + ".pdf"
        pdf = os.path.join(self.temp_dir, long_name)
        
        with open(pdf, 'w') as f:
            f.write("fake pdf")
        
        group = self.manager.create_new_group([pdf])
        
        assert group is not None


class TestConfigPersistence:
    """Tests para la persistencia de configuración."""
    
    def setup_method(self):
        """Configuración antes de cada test."""
        self.temp_dir = tempfile.mkdtemp()
        
    def teardown_method(self):
        """Limpieza después de cada test."""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_config_saves_base_path(self):
        """Test: La configuración guarda la ruta base."""
        manager = WorkspaceManager()
        manager.set_base_path(self.temp_dir)
        
        # Verificar que se guardó
        assert manager.base_path == self.temp_dir
        
        # Crear nuevo manager y verificar que carga
        manager2 = WorkspaceManager()
        
        # Debería cargar la configuración automáticamente
        assert manager2.base_path == self.temp_dir


def run_quick_test():
    """Ejecuta tests rápidos sin pytest."""
    print("=" * 60)
    print("🧪 EJECUTANDO TESTS RÁPIDOS DEL WORKSPACE")
    print("=" * 60)
    
    temp_dir = tempfile.mkdtemp()
    
    try:
        # Test 1: WorkGroup básico
        print("\n✅ Test 1: Crear WorkGroup...")
        group_path = os.path.join(temp_dir, "TestGroup")
        os.makedirs(group_path)
        # Crear subcarpetas manualmente para el test
        os.makedirs(os.path.join(group_path, "Origen"))
        os.makedirs(os.path.join(group_path, "Modificado - Sí"))
        os.makedirs(os.path.join(group_path, "Modificado - No"))
        
        group = WorkGroup(group_path)
        assert os.path.exists(group.origin_folder), f"origin_folder no existe: {group.origin_folder}"
        print("   ✓ WorkGroup creado correctamente")
        
        # Test 2: WorkspaceManager
        print("\n✅ Test 2: WorkspaceManager...")
        manager = WorkspaceManager()
        manager.base_path = None
        manager.work_groups = []
        manager.set_base_path(temp_dir)
        assert manager.is_workspace_active()
        print("   ✓ WorkspaceManager configurado")
        
        # Test 3: Crear grupo con PDFs
        print("\n✅ Test 3: Crear grupo con PDFs...")
        pdf = os.path.join(temp_dir, "test.pdf")
        with open(pdf, 'w') as f:
            f.write("fake pdf content")
        
        group = manager.create_new_group([pdf])
        assert group is not None, "Grupo no creado"
        assert group.get_pending_count() == 1, f"Pendientes: {group.get_pending_count()}"
        print(f"   ✓ Grupo creado: {group.name}")
        print(f"   ✓ PDFs pendientes: {group.get_pending_count()}")
        
        # Test 4: Verificar estructura de carpetas
        print("\n✅ Test 4: Estructura de carpetas...")
        assert os.path.exists(group.origin_folder), f"No existe: {group.origin_folder}"
        assert os.path.exists(group.modified_folder), f"No existe: {group.modified_folder}"
        assert os.path.exists(group.original_folder), f"No existe: {group.original_folder}"
        print("   ✓ Todas las carpetas existen")
        
        # Test 5: Estadísticas
        print("\n✅ Test 5: Estadísticas...")
        stats = manager.get_global_stats()
        assert stats['groups'] >= 1, f"Groups: {stats}"
        assert stats['pending'] >= 1, f"Pending: {stats}"
        print(f"   ✓ Grupos: {stats['groups']}")
        print(f"   ✓ Pendientes: {stats['pending']}")
        
        # Test 6: Múltiples grupos
        print("\n✅ Test 6: Múltiples grupos...")
        pdf2 = os.path.join(temp_dir, "test2.pdf")
        with open(pdf2, 'w') as f:
            f.write("fake pdf 2")
        
        group2 = manager.create_new_group([pdf2])
        assert group2 is not None
        assert group2.path != group.path, "Grupos deberían ser diferentes"
        print(f"   ✓ Segundo grupo creado: {group2.name}")
        
        # Test 7: Obtener todos los pendientes
        print("\n✅ Test 7: Obtener pendientes de todos los grupos...")
        total_pending = manager.get_all_pending_count()
        assert total_pending >= 2, f"Pendientes totales: {total_pending}"
        print(f"   ✓ Total pendientes: {total_pending}")
        
        print("\n" + "=" * 60)
        print("✅ TODOS LOS TESTS PASARON CORRECTAMENTE")
        print("=" * 60)
        
        return True
        
    except AssertionError as e:
        print(f"\n❌ TEST FALLIDO: {e}")
        import traceback
        traceback.print_exc()
        return False
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        shutil.rmtree(temp_dir)


if __name__ == "__main__":
    # Si se ejecuta directamente, correr tests rápidos
    run_quick_test()
