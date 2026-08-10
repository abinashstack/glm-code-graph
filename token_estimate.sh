#!/bin/bash

# Simple token estimate (1 token ≈ 4 bytes for Python code)

echo ""
echo "==================================================================================="
echo "                            TOKEN REDUCTION VERIFICATION"
echo "==================================================================================="
echo ""

# Find all Python files
echo "[1] Total files in codebase:"
all_files=0
total_size=0

for file in $(find . -name "*.py" -not -path "./__pycache__/*" -not -name "test_*.py"); do
    size=$(stat -c%s "$file")
    filename=$(basename "$file")
    echo "    $((all_files + 1)). $filename ($size bytes)"
    all_files=$((all_files + 1))
    total_size=$((total_size + size))
done

echo ""
echo "[2] Total size: $total_size bytes"
echo "[3] Traditional review: read all files ($all_files files)"

# Calculate blast radius for auth.py
echo ""
echo "==================================================================================="
echo "                            BLAST RADIUS ANALYSIS"
echo "==================================================================================="
echo ""
echo "[4] Reviewing changed file: auth.py"

# Find imports in auth.py
blast_files=0
blast_size=0
blast_list=()

# Get auth.py size
auth_size=$(stat -c%s "auth.py")
blast_list+=("auth.py ($auth_size bytes)")
blast_files=$((blast_files + 1))
blast_size=$((blast_size + auth_size))

echo ""
echo "    Import statements in auth.py:"

while IFS= read -r line; do
    trimmed=$(echo "$line" | sed 's/^[[:space:]]*//')
    if [[ $trimmed == import* ]] || [[ $trimmed == from* ]]; then
        echo "      - $trimmed"
        
        # Extract module name
        if [[ $trimmed == import* ]]; then
            module=$(echo "$trimmed" | sed 's/.*import[[:space:]]\([^[:space:]]*\).*/\1/' | cut -d. -f1)
        else
            module=$(echo "$trimmed" | sed 's/.*from[[:space:]]\([^[:space:]]*\).*/\1/')
        fi
        
        if [[ -f "$module.py" ]] && [[ $module != test_* ]]; then
            size=$(stat -c%s "$module.py")
            echo "    → Adding import: $module.py ($size bytes)"
            blast_list+=("$module.py ($size bytes)")
            blast_files=$((blast_files + 1))
            blast_size=$((blast_size + blast_size + size))
        fi
    fi
done < auth.py

# Find test files
test_count=$(find . -name "test_*.py" | wc -l)
if [[ $test_count -gt 0 ]]; then
    echo ""
    echo "    Test files found: $test_count file(s)"
    test_files=$(find . -name "test_*.py")
    for test_file in $test_files; do
        size=$(stat -c%s "$test_file")
        blast_list+=("$(basename $test_file) ($size bytes)")
        blast_files=$((blast_files + 1))
        blast_size=$((blast_size + size))
    done
fi

echo ""
echo "[5] Blast radius files ($blast_files total):"
for item in "${blast_list[@]}"; do
    echo "    $item"
done

echo ""
echo "[6] GLM Code Graph: read blast radius ($blast_files files, $blast_size bytes)"

# Calculate reduction
files_saved=$((all_files - blast_files))
size_reduction=$(awk "BEGIN {printf \"%.1f\", ($total_size - $blast_size) / $total_size * 100}")
token_reduction=$(awk "BEGIN {printf \"%.1f\", (1 - $blast_size / $total_size) * 100}")

# Calculate cost savings
cost_per_token=0.00001
review_cost=$(awk "BEGIN {printf \"%.4f\", $blast_size * $cost_per_token}")
saved_cost=$(awk "BEGIN {printf \"%.4f\", $total_size * $cost_per_token - $blast_size * $cost_per_token}")
monthly_savings=$(awk "BEGIN {printf \"%.2f\", $saved_cost * 100}")

echo ""
echo "==================================================================================="
echo "                            COMPARISON RESULTS"
echo "==================================================================================="
echo ""
echo "[7] Traditional Review:"
echo "    Files read:   $all_files"
echo "    Size:         $total_size bytes"
echo "    Tokens:       $((total_size / 4)) (≈ 4 bytes/token)"

echo ""
echo "[8] GLM Code Graph (Blast Radius):"
echo "    Files read:   $blast_files"
echo "                    ($files_saved files saved)"
echo "    Size:         $blast_size bytes"
echo "    Tokens:       $((blast_size / 4)) (≈ 4 bytes/token)"

echo ""
echo "[9] Reduction Metrics:"
echo "    Files:   $files_saved ($(awk "BEGIN {printf \"%.1f\", $files_saved / $all_files * 100}")% saved)"
echo "    Size:    $size_reduction% smaller"
echo "    Tokens:  $token_reduction% fewer"

echo ""
echo "[10] Expected Cost Savings:"
echo "    • Review cost: $${review_cost}"
echo "    • Saved: $${saved_cost}"
echo "    • Monthly savings (100 reviews): ~$$${monthly_savings}"

echo ""
echo "==================================================================================="
echo "                            CONCLUSION"
echo "==================================================================================="
echo ""
echo "✓ GLM Code Graph achieves $token_reduction% token reduction"
echo "✓ $files_saved files skipped per review"
echo "✓ Significant cost savings on frequent code reviews"
echo ""
