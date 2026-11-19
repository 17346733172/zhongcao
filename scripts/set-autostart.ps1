param(
    [switch]$Disable,
    [switch]$Check
)

$ErrorActionPreference = 'Stop'
if ($Disable -and $Check) { throw 'Use either -Disable or -Check, not both.' }

$bencaoRoot = Split-Path -Parent $PSScriptRoot
$bencaoEntry = Join-Path $PSScriptRoot 'start-at-logon.ps1'
$bencaoPowerShell = Join-Path $PSHOME 'powershell.exe'
$bencaoStartup = [Environment]::GetFolderPath('Startup')
if (-not $bencaoStartup) { throw 'Cannot locate the current user Startup folder.' }
$bencaoLink = Join-Path $bencaoStartup 'Bencao-Local.lnk'
$bencaoArguments = '-NoProfile -WindowStyle Hidden -File "' + $bencaoEntry + '"'
$bencaoShell = New-Object -ComObject WScript.Shell

if (Test-Path -LiteralPath $bencaoLink) {
    $shortcut = $bencaoShell.CreateShortcut($bencaoLink)
    $matches = $shortcut.TargetPath -eq $bencaoPowerShell -and
        $shortcut.Arguments -eq $bencaoArguments -and
        $shortcut.WorkingDirectory -eq $bencaoRoot
    if (-not $matches) {
        throw "A different startup entry exists at $bencaoLink. No changes made."
    }
    if ($Disable) {
        Remove-Item -LiteralPath $bencaoLink
        Write-Host 'Bencao login startup disabled. Running services are unaffected.'
        exit 0
    }
    Write-Host "Bencao login startup enabled: $bencaoLink"
    exit 0
}

if ($Disable) {
    Write-Host 'Bencao login startup is already disabled.'
    exit 0
}
if ($Check) {
    Write-Host 'Bencao login startup is disabled.'
    exit 1
}

if (-not (Test-Path -LiteralPath $bencaoEntry) -or
    -not (Test-Path -LiteralPath $bencaoPowerShell)) {
    throw 'Cannot find the Bencao login launcher or Windows PowerShell.'
}
New-Item -ItemType Directory -Path $bencaoStartup -Force | Out-Null
$shortcut = $bencaoShell.CreateShortcut($bencaoLink)
$shortcut.TargetPath = $bencaoPowerShell
$shortcut.Arguments = $bencaoArguments
$shortcut.WorkingDirectory = $bencaoRoot
$shortcut.Description = 'Start the local Bencao frontend and backend at Windows login.'
$shortcut.Save()
Write-Host "Bencao login startup enabled: $bencaoLink"
