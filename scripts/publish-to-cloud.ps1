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
        # Skip bare exit-code noise; only show real git messages
        $text = "{0}" -f $line
        if ($text -match '^\s*\d+\s*$') { continue }
        Write-Host $text
    }
    if ($null -eq $code) { $code = 0 }
    if ($code -ne 0) {
        Write-Host "[publish] git $($Args -join ' ')  → exit $code"
        Write-Error $FailMessage
        exit 1
    }
    # Do not return $code — PowerShell would print "0" to the console.
}

function Show-PushAuthHelp {
    Write-Host ""
    Write-Host "[publish] GitHub would not accept the push (sign-in missing or expired)."
    Write-Host "[publish] Fix once, then re-run:  RUNCPRP push"
    Write-Host ""
    Write-Host "  Option A — GitHub CLI (recommended):"
    Write-Host "    gh auth login"
    Write-Host "    (choose GitHub.com → HTTPS → Login with a web browser)"
    Write-Host "    gh auth setup-git"
    Write-Host "    RUNCPRP push"
    Write-Host ""
    Write-Host "  Option B — Git Credential Manager popup:"
    Write-Host "    git push origin main"
    Write-Host "    Sign in when the browser/popup appears, then re-run RUNCPRP push."
    Write-Host ""
}

function Invoke-GitPush {
    <#
    Push main to origin. Fails fast with clear auth help if credentials are missing
    (instead of hanging forever on a Credential Manager prompt).
    #>
    Write-Host "[publish] Pushing to GitHub (origin main)..."

    # Prefer gh if already logged in — wires git credentials automatically
    $gh = Get-Command gh -ErrorAction SilentlyContinue
    if ($gh) {
        $prev = $ErrorActionPreference
        $ErrorActionPreference = "Continue"
        $null = & gh auth status 2>&1
        $ghOk = ($LASTEXITCODE -eq 0)
        $ErrorActionPreference = $prev
        if ($ghOk) {
            & gh auth setup-git 2>$null | Out-Null
        }
    }

    $prev = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    # Give Credential Manager a window to finish; fail if still stuck
    $job = Start-Job -ScriptBlock {
        param($gitPath, $repoRoot)
        Set-Location $repoRoot
        & $gitPath push origin main 2>&1
        "___EXIT___$LASTEXITCODE"
    } -ArgumentList $git, $root

    $finished = Wait-Job $job -Timeout 90
    if (-not $finished) {
        Stop-Job $job -ErrorAction SilentlyContinue
        Remove-Job $job -Force -ErrorAction SilentlyContinue
        Write-Host "[publish] Push timed out after 90s (usually stuck on GitHub login)."
        Show-PushAuthHelp
        exit 1
    }

    $lines = @(Receive-Job $job)
    Remove-Job $job -Force -ErrorAction SilentlyContinue
    $ErrorActionPreference = $prev

    $code = 1
    foreach ($line in $lines) {
        $text = "{0}" -f $line
        if ($text -match '^___EXIT___(\d+)$') {
            $code = [int]$Matches[1]
            continue
        }
        if ($text.Trim().Length -gt 0) { Write-Host $text }
    }

    if ($code -ne 0) {
        Write-Host "[publish] git push origin main  → exit $code"
        Show-PushAuthHelp
        exit 1
    }
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
            Write-Host "[publish] Local is $ahead commit(s) ahead of GitHub (not uploaded yet)."
            Invoke-GitPush
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

Invoke-GitPush

Write-Host ""
Write-Host "[publish] SUCCESS - code is on GitHub."
Write-Host "[publish] Streamlit Community Cloud auto-redeploys from branch main"
Write-Host "[publish]   (usually 1-3 minutes). Refresh your public .streamlit.app URL."
Write-Host "[publish] Repo: https://github.com/imzcpr-blip/micro-range-selector"
exit 0
