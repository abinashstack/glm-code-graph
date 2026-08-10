# Token Reduction Verification Script for GLM Code Graph
# 1 token ≈ 4 bytes for Python code

Write-Host "`n$(('=' * 70))" -ForegroundColor Cyan
Write-Host " $((' ' * 15) + 'TOKEN REDUCTION VERIFICATION')" -ForegroundColor Cyan
Write-Host "$(('=' * 70))" -ForegroundColor Cyan

$repoPath = $PSScriptRoot

# Get all Python files
$allFiles = Get-ChildItem -Path $repoPath -Filter "*.py" -Recurse -File |
    Where-Object { $_.FullName -notmatch '__pycache__' -and $_.Name -notmatch 'test_' } |
    Sort-Object FullName

Write-Host "`n[1] Total files in codebase:" -ForegroundColor Yellow
for ($i = 0; $i -lt $allFiles.Count; $i++) {
    $file = $allFiles[$i]
    $size = $file.Length
    Write-Host "    $($i + 1). $($file.Name.PadRight(20)) $size bytes" -ForegroundColor White
}

# Calculate total
$totalSize = $allFiles | Measure-Object -Property Length -Sum | Select-Object -ExpandProperty Sum
Write-Host "`n[2] Total size: $($totalSize.ToString('N0')) bytes" -ForegroundColor Yellow

# Traditional approach
Write-Host "`n[3] Traditional review: read all files ($($allFiles.Count) files)" -ForegroundColor Yellow

# Blast radius for auth.py
Write-Host "`n$(('=' * 70))" -ForegroundColor Cyan
Write-Host " $((' ' * 18) + 'BLAST RADIUS ANALYSIS')" -ForegroundColor Cyan
Write-Host "$(('=' * 70))" -ForegroundColor Cyan

$reviewFile = "auth.py"
Write-Host "`n[4] Reviewing changed file: $reviewFile" -ForegroundColor Yellow

$blastFiles = @($reviewFile)
$blastSize = (Get-Item $reviewFile).Length

# Read auth.py and find imports
$content = Get-Content -Path $reviewFile -Raw

$importLines = $content -split "`n" | ForEach-Object { $_.Trim() } | Where-Object { $_ -match '^import |^from ' }

Write-Host "`n    Import statements in ${reviewFile}:" -ForegroundColor White
foreach ($imp in $importLines) {
    Write-Host "      - $imp" -ForegroundColor White

    # Extract module
    $module = ""
    if ($imp -match 'import (.+)') {
        $module = $matches[1].Split('.')[0].Trim()
    }
    else {
        $module = $imp.Split('from ')[1].Split(' import ')[0].Trim()
    }

    $modulePath = Join-Path $repoPath "$module.py"
    if (Test-Path $modulePath -PathType Leaf -Filter "*.py") {
        $size = (Get-Item $modulePath).Length
        Write-Host "    → Adding import: $module.py ($size bytes)" -ForegroundColor Green
        $blastFiles += @("$module.py")
        $blastSize += $size
    }
}

# Find test files
$testFiles = $allFiles | Where-Object { $_.Name -match 'test_' }
if ($testFiles.Count -gt 0) {
    Write-Host "`n    Test files: $($testFiles.Count) file(s)" -ForegroundColor Yellow
    foreach ($testFile in $testFiles) {
        $blastFiles += @($testFile.FullName)
        $blastSize += $testFile.Length
    }
}

Write-Host "`n[6] Blast radius files ($($blastFiles.Count) total):" -ForegroundColor Yellow
foreach ($file in $blastFiles) {
    $name = Split-Path $file -Leaf
    $size = (Get-Item $file).Length
    Write-Host "    $name`20s $size bytes" -ForegroundColor White
}

Write-Host "`n[7] GLM Code Graph: read blast radius ($($blastFiles.Count) files, $($blastSize.ToString('N0')) bytes)" -ForegroundColor Yellow

# Comparison
Write-Host "`n$(('=' * 70))" -ForegroundColor Cyan
Write-Host " $((' ' * 15) + 'COMPARISON RESULTS')" -ForegroundColor Cyan
Write-Host "$(('=' * 70))" -ForegroundColor Cyan

$filesSaved = $allFiles.Count - $blastFiles.Count
$sizeReduction = ($totalSize - $blastSize) / $totalSize * 100
$tokenReduction = ($totalSize - $blastSize) / $totalSize * 100

$costPerToken = 0.00001
$reviewCost = $blastSize * $costPerToken
$savedCost = ($totalSize * $costPerToken) - ($blastSize * $costPerToken)
$monthlySavings = $savedCost * 100

Write-Host "`n[8] Traditional Review:" -ForegroundColor Yellow
Write-Host "    Files read:   $($allFiles.Count)" -ForegroundColor White
Write-Host "    Size:         $($totalSize.ToString('N0')) bytes" -ForegroundColor White
Write-Host "    Tokens:       $($totalSize / 4) (≈ 4 bytes/token)" -ForegroundColor White

Write-Host "`n[9] GLM Code Graph (Blast Radius):" -ForegroundColor Yellow
Write-Host "    Files read:   $($blastFiles.Count)" -ForegroundColor White
Write-Host "                    ($filesSaved files saved)" -ForegroundColor Green
Write-Host "    Size:         $($blastSize.ToString('N0')) bytes" -ForegroundColor White
Write-Host "    Tokens:       $($blastSize / 4) (≈ 4 bytes/token)" -ForegroundColor White

Write-Host "`n[10] Reduction Metrics:" -ForegroundColor Yellow
$filesSavedPercent = $filesSaved / $allFiles.Count * 100
Write-Host "    Files:   $filesSaved ($filesSavedPercent:F1%)" -ForegroundColor Green
Write-Host "    Size:    $sizeReduction:F1% smaller" -ForegroundColor Green
Write-Host "    Tokens:  $tokenReduction:F1% fewer" -ForegroundColor Green

Write-Host "`n[11] Expected Cost Savings:" -ForegroundColor Yellow
Write-Host "    • Review cost: $${reviewCost:F4}" -ForegroundColor White
Write-Host "    • Saved: $${savedCost:F4}" -ForegroundColor Green
Write-Host "    • Monthly savings (100 reviews): ~$$${monthlySavings:F2}" -ForegroundColor Green

Write-Host "`n$(('=' * 70))" -ForegroundColor Cyan
Write-Host " $((' ' * 20) + 'CONCLUSION')" -ForegroundColor Cyan
Write-Host "$(('=' * 70))" -ForegroundColor Cyan
Write-Host "`n✓ GLM Code Graph achieves $tokenReduction:F1% token reduction" -ForegroundColor Green
Write-Host "✓ $filesSaved files skipped per review" -ForegroundColor Green
Write-Host "✓ Significant cost savings on frequent code reviews" -ForegroundColor Green
Write-Host "`n"
