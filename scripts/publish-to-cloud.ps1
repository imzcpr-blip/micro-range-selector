# Publish local CPRP / RUNCPRP changes to GitHub so Streamlit Community Cloud redeploys.
# Usage:
#   powershell -File scripts\publish-to-cloud.ps1
#   powershell -File scripts\publish-to-cloud.ps1 -Message "Update founder bio"
#   powershell -File scripts\publish-to-cloud.ps1 -SyncAssets

param(
    [string]$Message = "",
    [switch]$SyncAssets,
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"

$git = $null
foreach ($c in @("git", "C:\Program Files\Git\bin\git.exe", "C:\Program Files\Git\cmd\git.exe")) {
    try {
        if ($c -eq "git") {
            $cmd = Get-Command git -ErrorAction SilentlyContinue
            if ($cmd) { $git = $cmd.Source; break }
        } elseif (Test-Path $c) {
            $git = $c
            break
        }
    } catch { }
}
if (-not $git) {
    Write-Error "Git not found. Install Git for Windows, then re-open the terminal."
    exit 1
}

$root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
if (-not (Test-Path (Join-Path $root "app.py"))) {
    $root = "C:\Users\imzcp\micro-range-selector"
}
Set-Location $root

Write-Host "[publish] Project: $root"
Write-Host "[publish] Remote:  $(& $git remote get-url origin 2>$null)"
Write-Host "[publish] Branch:  $(& $git branch --show-current)"

if ($SyncAssets) {
    Write-Host "[publish] Syncing CPRP Trading docs/branding into assets..."
    python (Join-Path $root "sync_cprp_assets.py")
}

& $git add -A
$status = & $git status --porcelain
if (-not $status) {
    Write-Host "[publish] Nothing to commit - local tree matches last commit."
    if (-not $DryRun) {
        Write-Host "[publish] Fetching origin and rebasing onto latest main..."
        & $git fetch origin
        & $git pull --rebase origin main
        if ($LASTEXITCODE -ne 0) {
            Write-Error "git pull --rebase failed. Resolve conflicts, then retry."
            exit 1
        }
        $ahead = & $git rev-list --count "origin/main..HEAD" 2>$null
        if ($ahead -and [int]$ahead -gt 0) {
            Write-Host "[publish] Local is $ahead commit(s) ahead - pushing..."
            & $git push origin main
            if ($LASTEXITCODE -ne 0) { exit 1 }
            Write-Host "[publish] Done. Streamlit Cloud will redeploy from main shortly."
            exit 0
        }
    }
    Write-Host "[publish] Already in sync with origin. Public app needs no update."
    exit 0
}

Write-Host "[publish] Changes to publish:"
& $git status --short

if (-not $Message) {
    $stamp = Get-Date -Format "yyyy-MM-dd HH:mm"
    $Message = "Update CPRP Session Micro Selector - $stamp"
}

if ($DryRun) {
    Write-Host "[publish] Dry run - not committing or pushing."
    Write-Host "[publish] Would commit: $Message"
    exit 0
}

& $git commit -m $Message
if ($LASTEXITCODE -ne 0) {
    Write-Error "git commit failed."
    exit 1
}

# Integrate any remote commits before push (avoids "rejected non-fast-forward")
Write-Host "[publish] Fetching origin and rebasing onto latest main..."
& $git fetch origin
if ($LASTEXITCODE -ne 0) {
    Write-Error "git fetch failed."
    exit 1
}
& $git pull --rebase origin main
if ($LASTEXITCODE -ne 0) {
    Write-Host "[publish] Rebase hit conflicts. Resolve them, then run:"
    Write-Host "  git add -A"
    Write-Host "  git rebase --continue"
    Write-Host "  git push origin main"
    Write-Error "git pull --rebase failed."
    exit 1
}

Write-Host "[publish] Pushing to GitHub (origin)..."
& $git push origin main
if ($LASTEXITCODE -ne 0) {
    Write-Error "git push failed. Check GitHub sign-in / credentials, then retry."
    exit 1
}

Write-Host ""
Write-Host "[publish] SUCCESS - code is on GitHub."
Write-Host "[publish] Streamlit Community Cloud auto-redeploys from branch main"
Write-Host "[publish]   (usually 1-3 minutes). Refresh your public .streamlit.app URL."
Write-Host "[publish] Repo: https://github.com/imzcpr-blip/micro-range-selector"
exit 0
