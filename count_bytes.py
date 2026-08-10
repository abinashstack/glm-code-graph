#!/usr/bin/env python3
"""
Simple token reduction script using byte counting (1 token ≈ 4 bytes)
"""

import os
from pathlib import Path

def main():
    print("\n" + "=" * 70)
    print(" " * 15 + "TOKEN REDUCTION VERIFICATION")
    print("=" * 70)

    repo_path = Path(__file__).parent

    # Get all Python files
    all_files = []
    for py_file in repo_path.rglob("*.py"):
        if "__pycache__" not in str(py_file) and "test_" not in py_file.name:
            all_files.append(str(py_file))

    all_files.sort()

    print(f"\n[1] Total files in codebase:")
    for i, file_path in enumerate(all_files, 1):
        size = os.path.getsize(file_path)
        print(f"    {i}. {Path(file_path).name:20s} {size:6d} bytes")

    # Calculate total
    total_size = sum(os.path.getsize(f) for f in all_files)
    print(f"\n[2] Total size: {total_size:,} bytes")

    # Traditional approach
    print(f"\n[3] Traditional review: read all files ({len(all_files)} files)")

    # Blast radius for auth.py
    print("\n" + "=" * 70)
    print(" " * 18 + "BLAST RADIUS ANALYSIS")
    print("=" * 70)

    review_file = "auth.py"
    print(f"\n[4] Reviewing changed file: {review_file}")

    # Read auth.py and find imports
    blast_files = [review_file]
    blast_size = os.path.getsize(review_file)

    with open(os.path.join(repo_path, review_file), "r") as f:
        content = f.read()

    import_lines = [line.strip() for line in content.split('\n')
                    if line.strip().startswith('import ') or line.strip().startswith('from ')]

    print(f"\n    Import statements in {review_file}:")
    for imp in import_lines:
        print(f"      - {imp}")

        # Extract module
        if 'import ' in imp:
            module = imp.split('import ')[1].split('.')[0].strip()
        else:
            module = imp.split('from ')[1].split(' import ')[0].strip()

        module_path = os.path.join(repo_path, f"{module}.py")
        if os.path.exists(module_path) and "test_" not in module:
            blast_files.append(f"{module}.py")
            size = os.path.getsize(module_path)
            print(f"    → Adding import: {module}.py ({size} bytes)")
            blast_size += size

    # Find test files
    test_files = [f for f in all_files if "test_" in f]
    if test_files:
        print(f"\n    Test files: {len(test_files)} file(s)")
        for test_file in test_files:
            size = os.path.getsize(test_file)
            blast_files.append(test_file)
            blast_size += size

    print(f"\n[6] Blast radius files ({len(blast_files)} total):")
    for i, file_path in enumerate(blast_files, 1):
        size = os.path.getsize(file_path)
        print(f"    {i}. {Path(file_path).name:20s} {size:6d} bytes")

    print(f"\n[7] GLM Code Graph: read blast radius ({len(blast_files)} files, {blast_size:,} bytes)")

    # Comparison
    print("\n" + "=" * 70)
    print(" " * 15 + "COMPARISON RESULTS")
    print("=" * 70)

    files_saved = len(all_files) - len(blast_files)
    size_reduction = (total_size - blast_size) / total_size * 100
    token_reduction = (total_size - blast_size) / total_size * 100

    cost_per_token = 0.00001
    review_cost = blast_size * cost_per_token
    saved_cost = (total_size * cost_per_token) - (blast_size * cost_per_token)
    monthly_savings = saved_cost * 100

    print(f"\n[8] Traditional Review:")
    print(f"    Files read:   {len(all_files)}")
    print(f"    Size:         {total_size:,} bytes")
    print(f"    Tokens:       {total_size // 4} (≈ 4 bytes/token)")

    print(f"\n[9] GLM Code Graph (Blast Radius):")
    print(f"    Files read:   {len(blast_files)}")
    print(f"                    ({files_saved} files saved)")
    print(f"    Size:         {blast_size:,} bytes")
    print(f"    Tokens:       {blast_size // 4} (≈ 4 bytes/token)")

    print(f"\n[10] Reduction Metrics:")
    print(f"    Files:   {files_saved} ({files_saved/len(all_files)*100:.1f}% saved)")
    print(f"    Size:    {size_reduction:.1f}% smaller")
    print(f"    Tokens:  {token_reduction:.1f}% fewer")

    print(f"\n[11] Expected Cost Savings:")
    print(f"    • Review cost: ${review_cost:.4f}")
    print(f"    • Saved: ${saved_cost:.4f}")
    print(f"    • Monthly savings (100 reviews): ~${monthly_savings:.2f}")

    print("\n" + "=" * 70)
    print(" " * 20 + "CONCLUSION")
    print("=" * 70)
    print(f"\n✓ GLM Code Graph achieves {token_reduction:.1f}% token reduction")
    print(f"✓ {files_saved} files skipped per review")
    print(f"✓ Significant cost savings on frequent code reviews")
    print()

if __name__ == "__main__":
    main()
