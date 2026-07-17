<# Launch Claude Code with an explicit recursive-harness account silo.
   provenance: 2026-07-17 productization review - replace invisible profile pins. #>
[CmdletBinding()]
param(
  [Parameter(Position = 0, Mandatory = $true)][string]$Account,
  [Parameter(Position = 1, ValueFromRemainingArguments = $true)][string[]]$ClaudeArgs
)

$ErrorActionPreference = 'Stop'
if (-not $Account -or $Account.StartsWith('-') -or $Account -eq '.' -or
    $Account.Contains('..') -or $Account -notmatch '^[A-Za-z0-9._-]+$') {
  Write-Error "Invalid account '$Account' (letters, numbers, '.', '_', and '-' only)."
  exit 2
}

$configDir = Join-Path (Join-Path (Join-Path $PSScriptRoot '.claude-private') 'accounts') $Account
$settings = Join-Path $configDir 'settings.json'
if (-not (Test-Path -LiteralPath $configDir -PathType Container) -or
    -not (Test-Path -LiteralPath $settings -PathType Leaf)) {
  Write-Error "Account '$Account' is not initialized at $configDir. Run account-init.sh '$Account' --sync-settings from Git Bash."
  exit 1
}

$claude = Get-Command claude -ErrorAction SilentlyContinue
if (-not $claude) {
  Write-Error "'claude' is not on PATH."
  exit 127
}

$env:CLAUDE_CONFIG_DIR = (Resolve-Path -LiteralPath $configDir).Path
[Console]::Error.WriteLine("Harness account : {0}", $Account)
[Console]::Error.WriteLine("Config directory: {0}", $env:CLAUDE_CONFIG_DIR)
[Console]::Error.WriteLine("Checkout        : {0}", $PSScriptRoot)
& claude @ClaudeArgs
exit $LASTEXITCODE
