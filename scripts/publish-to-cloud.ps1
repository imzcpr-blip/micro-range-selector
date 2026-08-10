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

# Continue on native stderr (git writes progress to stderr even on success).
# We check $LASTEXITCODE ourselves after each git call.
$ErrorActionPreference = "Continue"

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

function Invoke-Git {
    param(
        [Parameter(Mandatory = $true)]
        [string[]]$Args,
        [string]$FailMessage = "git command failed."
    )
    # Run git; print all output lines (stdout + stderr) without treating stderr as fatal.
    $prev = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    $out = & $git @Args 2>&1
    $code = $LASTEXITCODE
    $ErrorActionPreference = $prev
    foreach ($line in $out) {
        Write-Host ("{0}" -f $line)
    }
    if ($null -eq $code) { $code = 0 }
    if ($code -ne 0) {
        Write-Host "[publish] git $($Args -join ' ')  → exit $code"
        Write-Error $FailMessage
        exit 1
    }
    return $code
}

function Sync-WithOrigin {
    <#
    Safer than `git pull --rebase origin main`, which on some Git/Windows setups
    fails with: "fatal: Cannot rebase onto multiple branches."
    Sequence: fetch refs, then rebase onto origin/main only.
    #>
    Write-Host "[publish] Fetching origin..."
    Invoke-Git -Args @("fetch", "origin") -FailMessage "git fetch failed. Check network / GitHub credentials."

    # Abort any stuck rebase/merge from a previous failed publish
    $rebaseMerge = Join-Path $root ".git\rebase-merge"
    $rebaseApply = Join-Path $root ".git\rebase-apply"
    if ((Test-Path $rebaseMerge) -or (Test-Path $rebaseApply)) {
        Write-Host "[publish] Clearing interrupted rebase state..."
        & $git rebase --abort 2>$null | Out-Null
    }

    Write-Host "[publish] Rebasing local main onto origin/main..."
    $prev = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    $out = & $git rebase origin/main 2>&1
    $code = $LASTEXITCODE
    $ErrorActionPreference = $prev
    foreach ($line in $out) { Write-Host ("{0}" -f $line) }

    if ($code -ne 0) {
        Write-Host ""
        Write-Host "[publish] Rebase failed (exit $code). Common fixes:"
        Write-Host "  1) If conflicts: resolve files, then:"
        Write-Host "       git add -A"
        Write-Host "       git rebase --continue"
        Write-Host "       git push origin main"
        Write-Host "  2) To cancel the rebase:"
        Write-Host "       git rebase --abort"
        Write-Host "  3) If stuck mid-rebase, run: git rebase --abort  then re-run this script."
        Write-Error "git rebase onto origin/main failed."
        exit 1
    }
}

Write-Host "[publish] Project: $root"
Write-Host "[publish] Remote:  $(& $git remote get-url origin 2>$null)"
Write-Host "[publish] Branch:  $(& $git branch --show-current)"

$branch = (& $git branch --show-current).Trim()
if ($branch -ne "main") {
    Write-Host "[publish] WARNING: current branch is '$branch' (expected main)."
}

if ($SyncAssets) {
    Write-Host "[publish] Syncing CPRP Trading docs/branding into assets..."
    python (Join-Path $root "sync_cprp_assets.py")
}

# Stage everything
& $git add -A 2>&1 | Out-Null
$status = & $git status --porcelain
if (-not $status) {
    Write-Host "[publish] Nothing to commit - local tree matches last commit."
    if (-not $DryRun) {
        Sync-WithOrigin
        $ahead = & $git rev-list --count "origin/main..HEAD" 2>$null
        if ($ahead -and [int]$ahead -gt 0) {
            Write-Host "[publish] Local is $ahead commit(s) ahead - pushing..."
            Invoke-Git -Args @("push", "origin", "main") -FailMessage "git push failed. Check GitHub sign-in / credentials."
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

Invoke-Git -Args @("commit", "-m", $Message) -FailMessage "git commit failed."

# Integrate any remote commits before push (avoids non-fast-forward reject)
Sync-WithOrigin

Write-Host "[publish] Pushing to GitHub (origin)..."
Invoke-Git -Args @("push", "origin", "main") -FailMessage "git push failed. Check GitHub sign-in / credentials, then retry."

Write-Host ""
Write-Host "[publish] SUCCESS - code is on GitHub."
Write-Host "[publish] Streamlit Community Cloud auto-redeploys from branch main"
Write-Host "[publish]   (usually 1-3 minutes). Refresh your public .streamlit.app URL."
Write-Host "[publish] Repo: https://github.com/imzcpr-blip/micro-range-selector"
exit 0
