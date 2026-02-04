#!/usr/bin/env python3
import re
import os

def fix_markdown(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    lines = content.split('\n')
    fixed = []
    
    for i, line in enumerate(lines):
        # Agregar línea en blanco antes de heading si es necesario
        if line.lstrip().startswith('#'):
            if fixed and fixed[-1].strip() and not fixed[-1].lstrip().startswith('#'):
                fixed.append('')
        
        fixed.append(line)
        
        # Agregar línea en blanco después de heading
        if line.lstrip().startswith('#'):
            if i < len(lines) - 1:
                next_line = lines[i + 1]
                if next_line.strip() and not next_line.lstrip().startswith('#'):
                    fixed.append('')
        
        # Agregar línea en blanco antes de lista
        if line.lstrip() and line.lstrip()[0] in '-*':
            if fixed and len(fixed) > 1:
                prev = fixed[-2] if len(fixed) > 1 else ''
                if prev.strip() and not prev.lstrip().startswith('#'):
                    if not prev.strip().startswith('|'):
                        if fixed[-1] != '':
                            fixed.insert(-1, '')
    
    result = '\n'.join(fixed)
    
    # Blank lines around code blocks
    result = re.sub(r'([^\n])\n```', r'\1\n\n```', result)
    result = re.sub(r'```\n([^\n])', r'```\n\n\1', result)
    
    # Language for code blocks
    result = re.sub(r'^```\n', '```python\n', result, flags=re.MULTILINE)
    
    # Remove duplicate blank lines
    result = re.sub(r'\n\n\n+', '\n\n', result)
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(result)
    
    return True

os.chdir(r'c:\Users\seto_\OneDrive\Escritorio\curriculum\PROYECTO 2026\modificar pdf')

files = [
    'DISTRIBUCION_ROLES_FASE2.md',
    'GITHUB_ISSUES_FASE2.md',
    'PHASE2_SESSION2_REPORT.md'
]

for f in files:
    if os.path.exists(f):
        fix_markdown(f)
        print(f'✅ {f}')
    else:
        print(f'❌ {f} no encontrado')
