# RunCPRP helper — start CPRP Session Micro Selector (Streamlit)
$ErrorActionPreference = "Stop"

$candidates = @(
    (Resolve-Path (Join-Path $PSScriptRoot "..\..\..\..") -ErrorAction SilentlyContinue).Path,
    "C:\Users\imzcp\micro-range-selector",
    "C:\Users\imzcp\OneDrive\Desktop\micro-range-selector"
) | Where-Object { $_ }

$root = $null
foreach ($c in $candidates) {
    if ($c -and (Test-Path (Join-Path $c "app.py")) -and (Test-Path (Join-Path $c "config.py"))) {
        $root = $c
        break
    }
}

if (-not $root) {
    Write-Error "CPRP project not found (expected app.py + config.py)."
    exit 1
}

Set-Location $root
Write-Host "RunCPRP — project: $root"

try {
    python -c "import streamlit" 2>$null
    if ($LASTEXITCODE -ne 0) { throw "missing streamlit" }
} catch {
    Write-Host "Installing requirements..."
    python -m pip install -r requirements.txt
}

Write-Host "Starting dashboard at http://localhost:8501 ..."
python -m streamlit run app.py --server.headless true
