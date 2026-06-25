<#
.SYNOPSIS
  Consolidate ONE fleet account's session store into the shared canonical store, then link it,
  so /resume sees every session from either account (ADR 0004). Native PowerShell - no bash.

.DESCRIPTION
  Lossless: never reduces the store. A longer shared transcript is taken only when the store
  copy is a strict byte-prefix of it (a pure append-continuation); a FORKED same-path copy is
  backed up (.forked.<ts>) before overwrite. The account's old projects/ is RENAMED to a
  .bak.<ts> (never deleted), and it refuses to cut over unless the store is already a complete
  superset. Then it links <account>/projects -> <store>/projects (SymbolicLink, falling back to
  a directory Junction if symlink privilege is missing).

  MUST run with no live session of the target account: Windows locks the folder of an open
  transcript, so the rename fails (cleanly, with a clear message and no changes) while a session
  of that account is open. A session of a DIFFERENT account, or no Claude at all, is fine.

.EXAMPLE
  powershell -ExecutionPolicy Bypass -File .\sync-account-sessions.ps1 wraith

.NOTES
  provenance: session b46882f7, 2026-06-25 - user runs rhen+wraith concurrently and wants
  /resume to span both; bash-only tool was unusable from Windows PowerShell.
#>
[CmdletBinding()]
param(
  [Parameter(Position = 0, Mandatory = $true)][string]$Account,
  [string]$StoreAccount = 'rhen',
  [string]$AccountsRoot
)

$ErrorActionPreference = 'Stop'

if (-not $AccountsRoot) { $AccountsRoot = Join-Path $PSScriptRoot '.claude-private\accounts' }

function Test-IsLink([string]$Path) {
  if (-not (Test-Path -LiteralPath $Path)) { return $false }
  $it = Get-Item -LiteralPath $Path -Force
  return [bool]($it.Attributes -band [System.IO.FileAttributes]::ReparsePoint)
}

function Get-RelPath([string]$Root, [string]$Full) {
  $r = $Root.TrimEnd('\', '/')
  if ($Full.StartsWith($r, [System.StringComparison]::OrdinalIgnoreCase)) {
    return $Full.Substring($r.Length).TrimStart('\', '/')
  }
  return $Full
}

# Is the (shorter) store file an exact byte-prefix of the (longer) source file?
function Test-StoreIsPrefixOfSource([string]$StoreFile, [string]$SrcFile) {
  $storeBytes = [System.IO.File]::ReadAllBytes($StoreFile)
  $fs = [System.IO.File]::Open($SrcFile, [System.IO.FileMode]::Open, [System.IO.FileAccess]::Read, [System.IO.FileShare]::ReadWrite)
  try {
    $buf = New-Object byte[] $storeBytes.Length
    $read = 0
    while ($read -lt $buf.Length) {
      $n = $fs.Read($buf, $read, $buf.Length - $read)
      if ($n -le 0) { break }
      $read += $n
    }
    if ($read -lt $storeBytes.Length) { return $false }
    for ($i = 0; $i -lt $storeBytes.Length; $i++) {
      if ($storeBytes[$i] -ne $buf[$i]) { return $false }
    }
    return $true
  } finally { $fs.Close() }
}

$store = Join-Path (Join-Path $AccountsRoot $StoreAccount) 'projects'
$src   = Join-Path (Join-Path $AccountsRoot $Account) 'projects'

if ($Account -eq $StoreAccount) { Write-Output "Account '$Account' OWNS the store; nothing to consolidate."; exit 0 }
if (-not (Test-Path -LiteralPath $store -PathType Container)) { Write-Error "Canonical store missing: $store"; exit 1 }

if (Test-IsLink $src) {
  $tgt = (Get-Item -LiteralPath $src -Force).Target
  Write-Output "$Account/projects is already a link -> $tgt. Nothing to do."
  exit 0
}
if (-not (Test-Path -LiteralPath $src -PathType Container)) { Write-Error "$Account/projects missing: $src"; exit 1 }

$ts        = Get-Date -Format 'yyyyMMdd-HHmmss'
$srcRoot   = (Resolve-Path -LiteralPath $src).Path
$storeRoot = (Resolve-Path -LiteralPath $store).Path

Write-Output "== Step 1: merge '$Account' into '$StoreAccount' store (add missing; take longer only if append-continuation) =="
$copied = 0; $forked = 0
Get-ChildItem -LiteralPath $src -Recurse -File -Filter *.jsonl | ForEach-Object {
  $rel = Get-RelPath $srcRoot $_.FullName
  $dst = Join-Path $storeRoot $rel
  if (-not (Test-Path -LiteralPath $dst)) {
    $dstDir = Split-Path -Parent $dst
    if (-not (Test-Path -LiteralPath $dstDir)) { New-Item -ItemType Directory -Path $dstDir -Force | Out-Null }
    Copy-Item -LiteralPath $_.FullName -Destination $dst
    $copied++; Write-Output "  + $rel"
  }
  else {
    $sLen = $_.Length
    $dLen = (Get-Item -LiteralPath $dst).Length
    if ($sLen -gt $dLen) {
      if (Test-StoreIsPrefixOfSource $dst $_.FullName) {
        Copy-Item -LiteralPath $_.FullName -Destination $dst -Force
        $copied++; Write-Output "  ^ $rel (store + appended tail)"
      }
      else {
        $bak = "$dst.forked.$ts"
        Copy-Item -LiteralPath $dst -Destination $bak -Force
        Copy-Item -LiteralPath $_.FullName -Destination $dst -Force
        $copied++; $forked++
        Write-Output "  ! $rel (FORKED: store copy diverged - backed up store -> $(Split-Path -Leaf $bak), took '$Account')"
      }
    }
  }
}
Write-Output "  merged $copied file(s); $forked forked-backup(s)."

Write-Output "== Step 2: safety gate - store must contain every '$Account' session by path =="
$missing = @()
Get-ChildItem -LiteralPath $src -Recurse -File -Filter *.jsonl | ForEach-Object {
  $rel = Get-RelPath $srcRoot $_.FullName
  if (-not (Test-Path -LiteralPath (Join-Path $storeRoot $rel))) { $missing += $rel }
}
if ($missing.Count -gt 0) { Write-Error "ABORT: $($missing.Count) '$Account' file(s) not in store: $($missing -join ', ')"; exit 1 }
Write-Output "  OK - store is a complete superset of '$Account'."

Write-Output "== Step 3: park '$Account/projects' and link it to the shared store =="
$bakDir = "$src.bak.$ts"
try {
  # Atomic .NET rename (single syscall). Unlike Move-Item, it does NOT fall back to a
  # non-atomic copy+delete on pwsh 7, so a locked source fails cleanly with NO partial .bak.
  [System.IO.Directory]::Move($src, $bakDir)
}
catch {
  Write-Output ""
  Write-Output "ERROR: could not move '$Account/projects' - a '$Account' session is almost certainly still open."
  Write-Output "       Windows locks the folder of an open transcript. Close ALL '$Account' Claude sessions and re-run."
  Write-Output "       No link change was made; Step 1's merge is additive and safe to re-run (idempotent)."
  Write-Output ("       details: {0}" -f $_.Exception.Message)
  exit 1
}

$linkType = $null
try {
  New-Item -ItemType SymbolicLink -Path $src -Target $storeRoot -ErrorAction Stop | Out-Null
  $linkType = 'SymbolicLink'
}
catch {
  try {
    New-Item -ItemType Junction -Path $src -Target $storeRoot -ErrorAction Stop | Out-Null
    $linkType = 'Junction'
  }
  catch {
    [System.IO.Directory]::Move($bakDir, $src)
    Write-Error "Could not create symlink or junction for '$Account/projects' (restored original): $($_.Exception.Message)"
    exit 1
  }
}

if (-not (Test-IsLink $src)) {
  Remove-Item -LiteralPath $src -Recurse -Force -ErrorAction SilentlyContinue
  [System.IO.Directory]::Move($bakDir, $src)
  Write-Error "Link creation did not produce a reparse point (restored original)."
  exit 1
}

$fossil = Join-Path (Join-Path $AccountsRoot $StoreAccount) 'projects.oldlink'
if (Test-IsLink $fossil) { Remove-Item -LiteralPath $fossil -Force; Write-Output "  removed stale fossil: $StoreAccount/projects.oldlink" }

Write-Output ""
Write-Output "DONE. '$Account' and '$StoreAccount' now share one session store via $linkType."
Write-Output "  $Account/projects -> $storeRoot"
Write-Output "  Parked copy: $bakDir  (delete once /resume from '$Account' is confirmed)."
exit 0
