#!/usr/bin/env python3
"""Script para corregir errores comunes de markdownlint"""

import re
import os

def fix_markdown(filepath):
    """Corrige errores comunes en archivos markdown"""
    
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    original = content
    
    # 1. Eliminar espacios finales (MD009)
    lines = content.split('\n')
    lines = [line.rstrip() for line in lines]
    content = '\n'.join(lines)
    
    # 2. Añadir línea en blanco antes de encabezados (MD022)
    # Pattern: detectar un encabezado sin línea en blanco antes
    content = re.sub(r'([^\n])\n(#{1,6} )', r'\1\n\n\2', content)
    
    # 3. Añadir línea en blanco después de encabezados (MD022)
    content = re.sub(r'(#{1,6} [^\n]*)\n([^\n# ])', r'\1\n\n\2', content)
    
    # 4. Arreglar espacios múltiples (MD012)
    while '\n\n\n' in content:
        content = content.replace('\n\n\n', '\n\n')
    
    # 5. Especificar lenguaje en bloques de código (MD040)
    # Detectar ``` seguido inmediatamente de una nueva línea sin lenguaje
    content = re.sub(r'```\n', '```text\n', content)
    content = re.sub(r'```text\n```', '```\n```', content)  # Evitar dobles
    
    # 6. Añadir línea en blanco antes de bloques de código (MD031)
    content = re.sub(r'([^\n])\n(```)', r'\1\n\n\2', content)
    
    # 7. Añadir línea en blanco después de bloques de código (MD031)
    content = re.sub(r'(```)\n([^\n])', r'\1\n\n\2', content)
    
    # 8. Línea en blanco alrededor de listas (MD032)
    content = re.sub(r'([^\n-])\n([-*] )', r'\1\n\n\2', content)
    content = re.sub(r'([-*] [^\n]*)\n([^\n-*])', r'\1\n\n\2', content)
    
    # 9. Limpiar múltiples espacios de nuevo
    while '\n\n\n' in content:
        content = content.replace('\n\n\n', '\n\n')
    
    # 10. Arreglar tablas - asegurar espacios alrededor de pipes (MD060)
    # Patrón simple: si vemos |x| sin espacios, agregar espacios
    lines = content.split('\n')
    table_lines = []
    for i, line in enumerate(lines):
        if '|' in line and not line.strip().startswith('|'):
            # No es tabla
            table_lines.append(line)
        elif '|' in line:
            # Posible tabla
            parts = line.split('|')
            # Asegurar espacios después del primer | y antes del último
            if len(parts) > 2:
                new_parts = []
                for j, part in enumerate(parts):
                    if j == 0 or j == len(parts) - 1:
                        new_parts.append(part)
                    else:
                        # Limpiar espacios y reassignar
                        new_parts.append(' ' + part.strip() + ' ')
                line = '|'.join(new_parts)
            table_lines.append(line)
        else:
            table_lines.append(line)
    
    content = '\n'.join(table_lines)
    
    # 11. Limpiar múltiples espacios uno más
    while '\n\n\n' in content:
        content = content.replace('\n\n\n', '\n\n')
    
    # Escribir solo si cambió
    if content != original:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        return True
    return False

# Archivos a procesar
files = [
    'ANALISIS_PROMPT_MEJORADO.md',
    'PROMPT_MEJORADO_v2.md',
    'COMPARATIVA_PROMPTS.md',
    'GUIA_LECTURA.md',
    'README_ANALISIS.md',
    'BUILD_STATUS.md'
]

print("Corrigiendo archivos markdown...")
print("=" * 60)

for filename in files:
    if os.path.exists(filename):
        if fix_markdown(filename):
            print(f"✓ Corregido: {filename}")
        else:
            print(f"• Sin cambios: {filename}")
    else:
        print(f"✗ No encontrado: {filename}")

print("=" * 60)
print("Proceso completado.")
