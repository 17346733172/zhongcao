$ErrorActionPreference = 'Stop'
$bencaoRoot = Split-Path -Parent $PSScriptRoot
$bencaoLogs = Join-Path $bencaoRoot 'tmp\local-servers'
New-Item -ItemType Directory -Path $bencaoLogs -Force | Out-Null

# Keep login startup silent, while preserving readiness errors for troubleshooting.
$bencaoPowerShell = Join-Path $PSHOME 'powershell.exe'
& $bencaoPowerShell -NoProfile -File (Join-Path $PSScriptRoot 'start-local.ps1') *> (Join-Path $bencaoLogs 'startup.log')
exit $LASTEXITCODE
