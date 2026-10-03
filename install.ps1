# Install cv-tailor for Codex and/or Claude Code (user level) on Windows, from a clone of
# this repo: links skills\cv-tailor into the agents' skill folders (directory junctions, no
# admin rights needed), then creates the skill environment.
#
#   .\install.ps1                 # codex + claude
#   .\install.ps1 -Targets codex  # only Codex   (%USERPROFILE%\.codex\skills\cv-tailor)
#   .\install.ps1 -Targets claude # only Claude  (%USERPROFILE%\.claude\skills\cv-tailor)
#
# Claude Code users can also install it as a plugin instead (see README).
param([string[]]$Targets = @("codex", "claude"))
$ErrorActionPreference = "Stop"
$src = Join-Path $PSScriptRoot "skills\cv-tailor"

foreach ($t in $Targets) {
    switch ($t) {
        "codex"  { $base = if ($env:CODEX_HOME) { $env:CODEX_HOME } else { Join-Path $HOME ".codex" }; $dest = Join-Path $base "skills\cv-tailor" }
        "claude" { $dest = Join-Path $HOME ".claude\skills\cv-tailor" }
        default  { throw "unknown target: $t (use codex or claude)" }
    }
    New-Item -ItemType Directory -Force (Split-Path $dest) | Out-Null
    if (Test-Path $dest) {
        $item = Get-Item $dest -Force
        if (-not ($item.Attributes -band [IO.FileAttributes]::ReparsePoint)) {
            Write-Host "skip ${t}: $dest exists and is not a link (remove it first)"; continue
        }
        $item.Delete()
    }
    New-Item -ItemType Junction -Path $dest -Target $src | Out-Null
    Write-Host "linked $dest -> $src"
}

python (Join-Path $src "cvt.py") setup-env
python (Join-Path $src "cvt.py") doctor
Write-Host "`nDone. Open your agent in an empty folder (your workspace) and paste a job offer."
