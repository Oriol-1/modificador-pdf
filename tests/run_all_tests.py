"""
Ejecutor de todos los tests de edición de texto.
================================================

Este script ejecuta todos los tests funcionales y de problemas reportados.

Uso: python tests/run_all_tests.py
"""

import os
import sys
import subprocess

def run_test_file(file_name):
    """Ejecuta un archivo de tests y retorna si fue exitoso."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    test_path = os.path.join(script_dir, file_name)
    
    if not os.path.exists(test_path):
        print(f"[!] Archivo no encontrado: {file_name}")
        return False
    
    # Usar utf-8 para evitar problemas de encoding con emojis
    env = os.environ.copy()
    env['PYTHONIOENCODING'] = 'utf-8'
    
    result = subprocess.run(
        [sys.executable, test_path],
        capture_output=True,
        text=True,
        encoding='utf-8',
        errors='replace',
        env=env
    )
    
    print(result.stdout)
    if result.stderr:
        # Filtrar warnings de CPU
        stderr_lines = [line for line in result.stderr.split('\n') 
                       if 'WARNING: CPU' not in line and 'WARNING: RDRND' not in line]
        if stderr_lines:
            print('\n'.join(stderr_lines))
    
    return result.returncode == 0


def main():
    print("\n" + "=" * 70)
    print("🧪 EJECUTANDO TODOS LOS TESTS DE EDICIÓN DE TEXTO")
    print("=" * 70)
    
    test_files = [
        "test_text_editing_functional.py",
        "test_reported_issues.py",
        "test_editor_complete.py"
    ]
    
    results = {}
    
    for test_file in test_files:
        print(f"\n📂 Ejecutando: {test_file}")
        print("-" * 70)
        results[test_file] = run_test_file(test_file)
    
    # Resumen final
    print("\n" + "=" * 70)
    print("📊 RESUMEN FINAL DE TODOS LOS TESTS")
    print("=" * 70)
    
    all_passed = all(results.values())
    
    for test_file, passed in results.items():
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"  {test_file}: {status}")
    
    print("\n" + "=" * 70)
    if all_passed:
        print("🎉 TODOS LOS TESTS PASAN - Sistema funcionando correctamente")
    else:
        print("⚠️ ALGUNOS TESTS FALLARON - Revisar errores arriba")
    print("=" * 70)
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
