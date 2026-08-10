#!/usr/bin/env python3
"""
Manual token reduction verification script.
Run this with: python token_reduction_manual.py
"""

import os
from pathlib import Path
import tiktoken

# Tokenizer for GLM-4 (similar to GPT-4)
ENCODING = tiktoken.encoding_for_model("gpt-4")

def count_tokens(content: str) -> int:
    """Count tokens in content."""
    return len(ENCODING.encode(content))

def get_file_size(file_path: str) -> int:
    """Get file size in bytes."""
    with open(file_path, "r", encoding="utf-8") as f:
        return len(f.read())

def main():
    repo_path = Path(__file__).parent
    
    print("\n" + "=" * 70)
    print(" " * 15 + "TOKEN REDUCTION VERIFICATION")
    print("=" * 70)
    
    # Get all files
    all_files = []
    for py_file in repo_path.rglob("*.py"):
        if "__pycache__" not in str(py_file) and "test_" not in py_file.name:
            all_files.append(str(py_file))
    
    all_files.sort()
    
    print(f"\n[1] Total files in codebase:")
    for i, file_path in enumerate(all_files, 1):
        size = get_file_size(file_path)
        print(f"    {i}. {Path(file_path).name:20s} {size:6d} bytes")
    
    # Calculate total
    total_size = sum(get_file_size(f) for f in all_files)
    print(f"\n[2] Total size: {total_size:,} bytes")
    
    # Read all content
    print(f"\n[3] Reading all files for traditional review...")
    all_content = ""
    for file_path in all_files:
        with open(file_path, "r", encoding="utf-8") as f:
            all_content += f.read() + "\n"
    
    all_tokens = count_tokens(all_content)
    print(f"    Total tokens: {all_tokens:,}")
    print(f"    Size: {len(all_content):,} bytes")
    
    # BLAST RADIUS ANALYSIS
    print("\n" + "=" * 70)
    print(" " * 18 + "BLAST RADIUS ANALYSIS")
    print("=" * 70)
    
    # Assume we're reviewing auth.py
    review_file = "auth.py"
    print(f"\n[4] Reviewing changed file: {review_file}")
    
    # Find all files that auth.py imports
    blast_files = [review_file]
    
    with open(os.path.join(repo_path, review_file), "r") as f:
        content = f.read()
        
        # Parse import statements
        import_lines = [
            line.strip() for line in content.split('\n')
            if line.strip().startswith('import ') or line.strip().startswith('from ')
        ]
        
        print(f"\n    Import statements in {review_file}:")
        for imp in import_lines:
            print(f"      - {imp}")
        
        # Extract modules
        for imp in import_lines:
            if 'import' in imp:
                module = imp.split('import ')[1].split('.')[0].strip()
            else:
                module = imp.split('from ')[1].split(' import ')[0].strip()
            
            module_path = os.path.join(repo_path, f"{module}.py")
            if os.path.exists(module_path) and "test_" not in module:
                blast_files.append(f"{module}.py")
                print(f"    → Adding import: {module}.py")
    
    # Find test files
    print(f"\n[5] Finding test files...")
    test_files = [f for f in all_files if "test_" in f]
    if test_files:
        print(f"    Test files: {', '.join([Path(f).name for f in test_files])}")
        blast_files.extend(test_files)
    
    print(f"\n[6] Blast radius files ({len(blast_files)} total):")
    for i, file_path in enumerate(blast_files, 1):
        size = get_file_size(file_path)
        print(f"    {i}. {Path(file_path).name:20s} {size:6d} bytes")
    
    # Calculate blast radius content
    print(f"\n[7] Reading blast radius files...")
    blast_content = ""
    for file_path in blast_files:
        with open(file_path, "r", encoding="utf-8") as f:
            blast_content += f.read() + "\n"
    
    blast_tokens = count_tokens(blast_content)
    blast_size = len(blast_content)
    
    print(f"    Total tokens: {blast_tokens:,}")
    print(f"    Size: {blast_size:,} bytes")
    
    # Comparison
    print("\n" + "=" * 70)
    print(" " * 15 + "COMPARISON RESULTS")
    print("=" * 70)
    
    files_saved = len(all_files) - len(blast_files)
    size_reduction = ((total_size - blast_size) / total_size) * 100
    token_reduction = ((all_tokens - blast_tokens) / all_tokens) * 100
    
    print(f"\n[8] Traditional Review:")
    print(f"    Files read:   {len(all_files)}")
    print(f"    Content size: {total_size:,} bytes")
    print(f"    Tokens:       {all_tokens:,}")
    
    print(f"\n[9] GLM Code Graph (Blast Radius):")
    print(f"    Files read:   {len(blast_files)}")
    print(f"                    ({files_saved} files saved)")
    print(f"    Content size: {blast_size:,} bytes")
    print(f"    Tokens:       {blast_tokens:,}")
    
    print(f"\n[10] Reduction Metrics:")
    print(f"    Files:   {files_saved} ({(files_saved/len(all_files)*100):.1f}% saved)")
    print(f"    Size:    {size_reduction:.1f}% smaller")
    print(f"    Tokens:  {token_reduction:.1f}% fewer")
    
    print(f"\n[11] Expected Cost Savings:")
    print(f"    • GLM-4 tokens: ${blast_tokens * 0.00001:.4f} per review")
    print(f"    • Saved: ${(all_tokens * 0.00001) - (blast_tokens * 0.00001):.4f} per review")
    print(f"    • Monthly review savings: ~${(all_tokens - blast_tokens) * 0.00001 * 100:.2f}")
    
    print("\n" + "=" * 70)
    print(" " * 20 + "CONCLUSION")
    print("=" * 70)
    print(f"\n✓ GLM Code Graph achieves {token_reduction:.1f}% token reduction")
    print(f"✓ {files_saved} files skipped per review")
    print(f"✓ Significant cost savings on frequent code reviews")
    print()

if __name__ == "__main__":
    main()
