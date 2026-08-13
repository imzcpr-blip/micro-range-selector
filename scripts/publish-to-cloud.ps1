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

$GitHubOwnerRepo = "imzcpr-blip/micro-range-selector"

function Write-GitLines {
    param($Lines)
    foreach ($line in @($Lines)) {
        if ($null -eq $line) { continue }
        if ($line -is [System.Management.Automation.ErrorRecord]) {
            $text = $line.ToString()
        } else {
            $text = "$line"
        }
        if ($text -match '^\s*\d+\s*$') { continue }
        if ($text.Trim().Length -gt 0) { Write-Host $text }
    }
}

function Invoke-Git {
    param(
        [Parameter(Mandatory = $true)]
        [string[]]$Args,
        [string]$FailMessage = "git command failed."
    )
    $prev = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    $out = & $git @Args 2>&1
    $code = $LASTEXITCODE
    $ErrorActionPreference = $prev
    Write-GitLines $out
    if ($null -eq $code) { $code = 0 }
    if ($code -ne 0) {
        Write-Host "[publish] git $($Args -join ' ')  -> exit $code"
        Write-Error $FailMessage
        exit 1
    }
}

function Show-PushAuthHelp {
    # Use single-quoted strings only (no special dash characters).
    Write-Host ''
    Write-Host '[publish] GitHub would not accept the push (sign-in missing or expired).'
    Write-Host '[publish] Fix once, then re-run:  RUNCPRP push'
    Write-Host ''
    Write-Host '  1) gh auth login'
    Write-Host '     (GitHub.com -> HTTPS -> Login with a web browser)'
    Write-Host '  2) gh auth setup-git'
    Write-Host '  3) RUNCPRP push'
    Write-Host ''
}

function Invoke-GitPush {
    Write-Host '[publish] Pushing to GitHub (origin main)...'
    Write-Host '[publish] (Large branding files can take a minute - please wait.)'

    $prev = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    $code = 1

    $gh = Get-Command gh -ErrorAction SilentlyContinue
    $token = $null
    if ($gh) {
        $null = & gh auth status 2>&1
        if ($LASTEXITCODE -eq 0) {
            $token = (& gh auth token 2>$null | Out-String).Trim()
        }
    }

    if ($token -and $token.Length -ge 20) {
        Write-Host '[publish] Auth: GitHub CLI token (no popup)...'
        $pushUrl = "https://x-access-token:${token}@github.com/${GitHubOwnerRepo}.git"
        $out = & $git -c credential.helper= -c http.version=HTTP/1.1 push $pushUrl "HEAD:main" 2>&1
        $code = $LASTEXITCODE
        Write-GitLines $out
    } else {
        Write-Host '[publish] gh token unavailable - trying plain git push...'
        $out = & $git -c http.version=HTTP/1.1 push origin main 2>&1
        $code = $LASTEXITCODE
        Write-GitLines $out
    }

    $ErrorActionPreference = $prev
    if ($null -eq $code) { $code = 0 }

    if ($code -ne 0) {
        Write-Host "[publish] git push failed (exit $code)."
        Show-PushAuthHelp
        exit 1
    }

    & $git fetch origin main 2>$null | Out-Null
    Write-Host '[publish] Push complete.'
}

function Sync-WithOrigin {
    Write-Host '[publish] Fetching origin...'
    Invoke-Git -Args @("fetch", "origin") -FailMessage "git fetch failed. Check network / GitHub credentials."

    $rebaseMerge = Join-Path $root ".git\rebase-merge"
    $rebaseApply = Join-Path $root ".git\rebase-apply"
    if ((Test-Path $rebaseMerge) -or (Test-Path $rebaseApply)) {
        Write-Host '[publish] Clearing interrupted rebase state...'
        & $git rebase --abort 2>$null | Out-Null
    }

    Write-Host '[publish] Rebasing local main onto origin/main...'
    $prev = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    $out = & $git rebase origin/main 2>&1
    $code = $LASTEXITCODE
    $ErrorActionPreference = $prev
    Write-GitLines $out

    if ($code -ne 0) {
        Write-Host ''
        Write-Host "[publish] Rebase failed (exit $code). Common fixes:"
        Write-Host '  1) Resolve conflicts, then: git add -A ; git rebase --continue ; git push origin main'
        Write-Host '  2) Cancel: git rebase --abort'
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
    Write-Host '[publish] Syncing CPRP Trading docs/branding into assets...'
    python (Join-Path $root "sync_cprp_assets.py")
}

& $git add -A 2>&1 | Out-Null
$status = & $git status --porcelain
if (-not $status) {
    Write-Host '[publish] Nothing to commit - local tree matches last commit.'
    if (-not $DryRun) {
        Sync-WithOrigin
        $ahead = & $git rev-list --count "origin/main..HEAD" 2>$null
        if ($ahead -and [int]$ahead -gt 0) {
            Write-Host "[publish] Local is $ahead commit(s) ahead of GitHub (not uploaded yet)."
            Invoke-GitPush
            Write-Host '[publish] Done. Streamlit Cloud will redeploy from main shortly.'
            exit 0
        }
    }
    Write-Host '[publish] Already in sync with origin. Public app needs no update.'
    exit 0
}

Write-Host '[publish] Changes to publish:'
& $git status --short

if (-not $Message) {
    $stamp = Get-Date -Format "yyyy-MM-dd HH:mm"
    $Message = "Update CPRP Session Micro Selector - $stamp"
}

if ($DryRun) {
    Write-Host '[publish] Dry run - not committing or pushing.'
    Write-Host "[publish] Would commit: $Message"
    exit 0
}

Invoke-Git -Args @("commit", "-m", $Message) -FailMessage "git commit failed."

Sync-WithOrigin

Invoke-GitPush

Write-Host ''
Write-Host '[publish] SUCCESS - code is on GitHub.'
Write-Host '[publish] Streamlit Community Cloud auto-redeploys from branch main'
Write-Host '[publish]   (usually 1-3 minutes). Refresh your public .streamlit.app URL.'
Write-Host "[publish] Repo: https://github.com/$GitHubOwnerRepo"
exit 0