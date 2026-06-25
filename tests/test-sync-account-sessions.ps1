#requires -Version 5.1
# Regression test for ../sync-account-sessions.ps1 (the Windows-native session-store cutover).
# Runs the ACTUAL script as a child process against throwaway sandbox accounts and asserts the
# filesystem outcome. Pass -Runtime to choose which PowerShell runs the cutover:
#   powershell -ExecutionPolicy Bypass -File tests\test-sync-account-sessions.ps1 -Runtime powershell
#   pwsh       -ExecutionPolicy Bypass -File tests\test-sync-account-sessions.ps1 -Runtime pwsh
# provenance: session b46882f7, 2026-06-25 — bash tool was unusable from Windows PowerShell; this
# proves the native replacement is lossless + lock-safe under BOTH PS 5.1 and pwsh 7.
param(
  [string]$ScriptPath = (Join-Path (Split-Path -Parent $PSScriptRoot) 'sync-account-sessions.ps1'),
  [string]$Runtime    = 'powershell'   # exe used to RUN the cutover (child): 'powershell' (5.1) or 'pwsh' (7)
)
$ErrorActionPreference = 'Stop'

$script:pass = 0; $script:fail = 0
function Assert([string]$name, [bool]$cond) {
  if ($cond) { $script:pass++; Write-Host ("  PASS  " + $name) -ForegroundColor Green }
  else       { $script:fail++; Write-Host ("  FAIL  " + $name) -ForegroundColor Red }
}
function ReadText([string]$p) { if (Test-Path -LiteralPath $p) { [System.IO.File]::ReadAllText($p) } else { $null } }
function WriteText([string]$p, [string]$t) {
  $d = Split-Path -Parent $p
  if (-not (Test-Path -LiteralPath $d)) { New-Item -ItemType Directory -Path $d -Force | Out-Null }
  [System.IO.File]::WriteAllText($p, $t)
}
function IsLink([string]$p) {
  if (-not (Test-Path -LiteralPath $p)) { return $false }
  [bool]((Get-Item -LiteralPath $p -Force).Attributes -band [System.IO.FileAttributes]::ReparsePoint)
}
function New-Sandbox {
  $root = Join-Path $env:TEMP ("synctest-" + (Get-Date -Format 'yyyyMMddHHmmssfff') + "-" + (Get-Random))
  $rp = Join-Path $root 'accounts\rhen\projects\proj'
  $wp = Join-Path $root 'accounts\wraith\projects\proj'
  New-Item -ItemType Directory -Path $rp -Force | Out-Null
  New-Item -ItemType Directory -Path $wp -Force | Out-Null
  # shared, identical
  WriteText (Join-Path $rp 'common.jsonl')    "C1`nC2`n"
  WriteText (Join-Path $wp 'common.jsonl')    "C1`nC2`n"
  # append-continuation: store is a strict byte-prefix of source -> take source, NO backup
  WriteText (Join-Path $rp 'appendsrc.jsonl') "A1`nA2`n"
  WriteText (Join-Path $wp 'appendsrc.jsonl') "A1`nA2`nA3`n"
  # forked: source longer but diverged -> back up store, take source
  WriteText (Join-Path $rp 'forked.jsonl')    "F1`nF2`n"
  WriteText (Join-Path $wp 'forked.jsonl')    "FX`nFY`nFZ`n"
  # store-only (must remain untouched)
  WriteText (Join-Path $rp 'storeonly.jsonl') "S1`n"
  # source-only (must be copied in)
  WriteText (Join-Path $wp 'srconly.jsonl')   "R1`nR2`n"
  # nested source-only (tests recursion + dir creation)
  WriteText (Join-Path $wp 'sub\agent-1.jsonl') "N1`n"
  return $root
}
function Run-Cutover([string]$root) {
  $out = & $Runtime -NoProfile -ExecutionPolicy Bypass -File $ScriptPath 'wraith' -StoreAccount 'rhen' -AccountsRoot (Join-Path $root 'accounts') 2>&1
  return [pscustomobject]@{ Code = $LASTEXITCODE; Out = ($out | Out-String) }
}

Write-Host ("=== Test suite (cutover run under: {0}) ===" -f $Runtime) -ForegroundColor Cyan

# ----------------------------------------------------------------------------
Write-Host "`n[T1] happy path: lossless union + link + parked .bak + forked backup"
$root = New-Sandbox
$store = Join-Path $root 'accounts\rhen\projects'
$wproj = Join-Path $root 'accounts\wraith\projects'
$r1 = Run-Cutover $root
Assert "exit code 0" ($r1.Code -eq 0)
Assert "wraith/projects is now a reparse point (link)" (IsLink $wproj)
$tgt = (Get-Item -LiteralPath $wproj -Force).Target
Assert "link target resolves to rhen/projects" ((Resolve-Path -LiteralPath $tgt).Path -eq (Resolve-Path -LiteralPath $store).Path)
# union present & correct in the store
Assert "source-only copied (srconly)"          ((ReadText (Join-Path $store 'proj\srconly.jsonl'))   -eq "R1`nR2`n")
Assert "nested source-only copied (sub/agent-1)" ((ReadText (Join-Path $store 'proj\sub\agent-1.jsonl')) -eq "N1`n")
Assert "append-continuation taken (appendsrc=src)" ((ReadText (Join-Path $store 'proj\appendsrc.jsonl')) -eq "A1`nA2`nA3`n")
Assert "forked: store now holds source copy"   ((ReadText (Join-Path $store 'proj\forked.jsonl'))   -eq "FX`nFY`nFZ`n")
$forkBak = Get-ChildItem -LiteralPath (Join-Path $store 'proj') -Filter 'forked.jsonl.forked.*' -ErrorAction SilentlyContinue
Assert "forked: original store copy backed up (.forked.*)" ($forkBak -and ((ReadText $forkBak[0].FullName) -eq "F1`nF2`n"))
Assert "store-only untouched (storeonly)"       ((ReadText (Join-Path $store 'proj\storeonly.jsonl')) -eq "S1`n")
Assert "shared-identical untouched (common)"    ((ReadText (Join-Path $store 'proj\common.jsonl'))    -eq "C1`nC2`n")
# parked backup of the original source
$bak = Get-ChildItem -LiteralPath (Split-Path -Parent $wproj) -Directory -Filter 'projects.bak.*'
Assert "wraith/projects parked to exactly one .bak" ($bak.Count -eq 1)
Assert "parked .bak still has original source srconly" ((ReadText (Join-Path $bak[0].FullName 'proj\srconly.jsonl')) -eq "R1`nR2`n")
# reading THROUGH the link shows the union (it IS the store)
$linkCount = (Get-ChildItem -LiteralPath $wproj -Recurse -File -Filter *.jsonl).Count
$storeCount = (Get-ChildItem -LiteralPath $store -Recurse -File -Filter *.jsonl).Count
Assert "reading via link == reading the store (same file count)" ($linkCount -eq $storeCount -and $linkCount -gt 0)

# ----------------------------------------------------------------------------
Write-Host "`n[T2] idempotency: re-running is a no-op"
$r2 = Run-Cutover $root
Assert "second run exit 0" ($r2.Code -eq 0)
Assert "second run reports 'already a link'" ($r2.Out -match 'already a link')
$bak2 = Get-ChildItem -LiteralPath (Split-Path -Parent $wproj) -Directory -Filter 'projects.bak.*'
Assert "no second .bak created" ($bak2.Count -eq 1)
Remove-Item -LiteralPath $root -Recurse -Force -ErrorAction SilentlyContinue

# ----------------------------------------------------------------------------
Write-Host "`n[T3] open-file lock: clean abort, no changes, then succeeds once released"
$root = New-Sandbox
$wproj = Join-Path $root 'accounts\wraith\projects'
$held = Join-Path $wproj 'proj\common.jsonl'
# Claude holds the transcript open with FileShare.Read; that still blocks renaming the parent dir.
$fs = [System.IO.File]::Open($held, [System.IO.FileMode]::Open, [System.IO.FileAccess]::Read, [System.IO.FileShare]::Read)
try {
  $r3 = Run-Cutover $root
  Assert "locked run exits non-zero" ($r3.Code -ne 0)
  Assert "locked run explains a session is still open" ($r3.Out -match 'still open')
  Assert "wraith/projects still a real dir (NOT linked)" (-not (IsLink $wproj))
  $bakL = Get-ChildItem -LiteralPath (Split-Path -Parent $wproj) -Directory -Filter 'projects.bak.*' -ErrorAction SilentlyContinue
  Assert "no .bak left behind by the aborted run" ((@($bakL)).Count -eq 0)
}
finally { $fs.Close() }
$r4 = Run-Cutover $root
Assert "after releasing the lock, cutover succeeds (exit 0)" ($r4.Code -eq 0)
Assert "wraith/projects now linked" (IsLink $wproj)
Remove-Item -LiteralPath $root -Recurse -Force -ErrorAction SilentlyContinue

# ----------------------------------------------------------------------------
$resultColor = 'Green'; if ($script:fail -gt 0) { $resultColor = 'Red' }
Write-Host ("`n=== RESULT: {0} passed, {1} failed ===" -f $script:pass, $script:fail) -ForegroundColor $resultColor
if ($script:fail -gt 0) { exit 1 } else { exit 0 }
