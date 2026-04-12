"""Fix corrupted code fences in PLAN_MERGE_REORDER_PAGES.md.

The previous inline Python command had backticks eaten by PowerShell,
resulting in corrupted lines. This script replaces them with proper fences.
"""
import re

with open('PLAN_MERGE_REORDER_PAGES.md', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# The corrupted pattern is: two backslashes + tab + "ext" + newline
# In bytes: b'\\\\\text\n' where \t is actual tab (0x09)
corrupted = '\\\\\text\n'
replacement = '\x60\x60\x60text\n'  # ```text

fixed = 0
for i in range(len(lines)):
    if lines[i] == corrupted:
        lines[i] = replacement
        fixed += 1
        print(f"Fixed L{i+1}")

print(f"\nTotal fixed: {fixed}")

with open('PLAN_MERGE_REORDER_PAGES.md', 'w', encoding='utf-8') as f:
    f.writelines(lines)

print("File saved.")
"""Fix corrupted code fences in PLAN_MERGE_REORDER_PAGES.md"""

with open('PLAN_MERGE_REORDER_PAGES.md', 'r', encoding='utf-8') as f:
    lines = f.readlines()

fence_text = "\x60\x60\x60text\n"  # ```text using hex to avoid shell escaping

fixed = 0
for i in range(len(lines)):
    s = lines[i].strip()
    if s == '\\\\\\text' or s == '\\\\text' or s == '\\\\\\\\text':
        lines[i] = fence_text
        fixed += 1
        print(f"Fixed L{i+1}")

print(f"Fixed {fixed} lines")

with open('PLAN_MERGE_REORDER_PAGES.md', 'w', encoding='utf-8') as f:
    f.writelines(lines)
print("File saved.")
