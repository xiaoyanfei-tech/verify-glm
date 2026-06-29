# Install verify-glm skill to %USERPROFILE%\.claude\skills\
# PowerShell installer

$ErrorActionPreference = "Stop"

$src = Join-Path $PSScriptRoot "skills\verify-glm"
$dest = Join-Path $env:USERPROFILE ".claude\skills\verify-glm"

if (-not (Test-Path $src)) {
    Write-Error "Source dir not found: $src"
    exit 1
}

$parent = Split-Path $dest -Parent
if (-not (Test-Path $parent)) {
    New-Item -ItemType Directory -Path $parent -Force | Out-Null
}

if (Test-Path $dest) {
    Write-Host "Updating existing skill at $dest"
    Remove-Item -Recurse -Force $dest
}

Copy-Item -Recurse $src $dest

Write-Host "[OK] Installed: $dest" -ForegroundColor Green
Write-Host ""
Write-Host "Test it:"
Write-Host "  python `"$dest\verify_glm.py`""
