param(
    [string]$Account,
    [switch]$AllAccounts,
    [switch]$GlobalLegacy
)

$ErrorActionPreference = 'Stop'
$repo = Split-Path -Parent $MyInvocation.MyCommand.Path
$bashCandidates = @(
    (Get-Command bash -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Source -ErrorAction SilentlyContinue),
    (Join-Path ${env:ProgramFiles} 'Git\bin\bash.exe')
) | Where-Object { $_ -and (Test-Path -LiteralPath $_) } | Select-Object -Unique

if (-not $bashCandidates) {
    throw 'Git Bash is required by the supported Windows distribution contract.'
}
if ($Account -and $AllAccounts) {
    throw '-Account and -AllAccounts are mutually exclusive.'
}

$arguments = @((Join-Path $repo 'uninstall.sh'))
if ($Account) { $arguments += @('--account', $Account) }
if ($AllAccounts) { $arguments += '--all-accounts' }
if ($GlobalLegacy) { $arguments += '--global-legacy' }

& $bashCandidates[0] @arguments
exit $LASTEXITCODE

