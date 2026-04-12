"""Diagnose code fence corruption in PLAN_MERGE_REORDER_PAGES.md"""

with open('PLAN_MERGE_REORDER_PAGES.md', 'r', encoding='utf-8') as f:
    lines = f.readlines()

print(f"Total lines: {len(lines)}")
print()

# Find all code fence lines and lines that look like they should be
for i in range(len(lines)):
    s = lines[i].strip()
    # Any line with backticks
    if s.startswith('`') and len(s) < 20:
        print(f"L{i+1}: {repr(s)}")
    # Lines with backslash-backtick patterns
    if '\\`' in s:
        print(f"L{i+1} (escaped): {repr(s[:50])}")
    # ASCII art (should be inside code blocks)
    if s.startswith('\u250c'):
        print(f"L{i+1} (ascii-art): starts with box char")
"""Fix code fences that were corrupted by escape issues."""
import sys

with open('PLAN_MERGE_REORDER_PAGES.md', 'r', encoding='utf-8') as f:
    lines = f.readlines()

fence = '```'
fence_text = '```text'

# The previous script replaced code fence lines with escaped backtick strings
# which resulted in empty/wrong lines. Find and fix them.
# We need to find lines that SHOULD be code fences but aren't.

# Known positions (adjusted for 4 inserted blank lines):
# Original L85 -> now L86 (after 1 insertion at L55)
# Original L119 -> now L121 (after 2 insertions)
# Original L611 -> now L615 (after 4 insertions)
# Original L649 -> now L653
# Original L878 -> now L882
# Original L912 -> now L916

# Let me find them by looking at context
fixes_applied = 0

for i in range(len(lines)):
    stripped = lines[i].strip()
    # Check for corrupted fence lines (the escaped backticks became something else)
    # The \`\`\`text strings became something like `\`\`text or similar garbage
    if stripped in ('\\`\\`\\`text', '``text', '`text', ''):
        # Check if surrounding lines suggest this was a code fence
        # Look for code content nearby
        pass

# Actually, let me just search for specific patterns.
# After the previous script, the code fence lines that should be ```text
# were set to the string with escaped backticks.
# Let me check what they actually became:
print(f"Total lines: {len(lines)}")

# Let me find all lines that look like they should be opening code fences
# by looking for known context
for i in range(len(lines)):
    line = lines[i]
    # Find ASCII art diagram starts (should be ```text blocks)
    if '┌──────' in line and i > 0:
        prev = lines[i-1].strip()
        if prev != '```text' and prev != '```':
            print(f"L{i+1}: ASCII art without code fence above. L{i}: {repr(lines[i-1][:50])}")
    # Find known diagram patterns
    if line.strip().startswith('Fase 1 ───') and i > 0:
        prev = lines[i-1].strip()
        if prev != '```text' and prev != '```':
            print(f"L{i+1}: Diagram without code fence above. L{i}: {repr(lines[i-1][:50])}")
    if line.strip().startswith('Semana 1:') and i > 0:
        prev = lines[i-1].strip()
        if prev != '```text' and prev != '```':
            print(f"L{i+1}: Timeline without code fence above. L{i}: {repr(lines[i-1][:50])}")
    if line.strip().startswith('core/page_identity.py') and '──' in line and i > 0:
        prev = lines[i-1].strip()
        if prev != '```text' and prev != '```':
            print(f"L{i+1}: Dep diagram without code fence above. L{i}: {repr(lines[i-1][:50])}")

# Also check: lines that start numbered items inside what should be a code fence
# "1. Usuario abre menú"
for i in range(len(lines)):
    line = lines[i].strip()
    if line == '1. Usuario abre menú "Documento → Insertar PDF..." (o Ctrl+Shift+I)':
        if i > 0:
            prev = lines[i-1].strip()
            print(f"L{i+1}: Insert flow without code fence above. L{i}: {repr(lines[i-1][:50])}")
