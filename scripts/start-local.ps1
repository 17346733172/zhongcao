param(
    [switch]$Check,
    [ValidateRange(10, 600)][int]$TimeoutSeconds = 240
)

$ErrorActionPreference = 'Stop'
$bencaoRoot = Split-Path -Parent $PSScriptRoot
$bencaoLogs = Join-Path $bencaoRoot 'tmp\local-servers'

function Test-BencaoEndpoint([string]$Url, [string]$Expected) {
    $response = $null
    $reader = $null
    try {
        $request = [System.Net.HttpWebRequest]::Create($Url)
        $request.Proxy = $null
        $request.Timeout = 3000
        $request.ReadWriteTimeout = 3000
        $response = $request.GetResponse()
        $reader = New-Object System.IO.StreamReader($response.GetResponseStream())
        return ($response.StatusCode -eq 200 -and $reader.ReadToEnd().Contains($Expected))
    } catch {
        return $false
    } finally {
        if ($null -ne $reader) { $reader.Dispose() }
        if ($null -ne $response) { $response.Dispose() }
    }
}

function Start-BencaoService([string]$Name, [string]$Launcher, [string]$Url, [string]$Expected) {
    if (Test-BencaoEndpoint $Url $Expected) {
        Write-Host "$Name is already ready."
        return
    }
    $launcherPath = Join-Path $bencaoRoot $Launcher
    $existing = Get-CimInstance Win32_Process -Filter "Name = 'cmd.exe'" | Where-Object {
        $_.CommandLine -and $_.CommandLine.IndexOf($launcherPath, [StringComparison]::OrdinalIgnoreCase) -ge 0
    }
    if ($existing) {
        Write-Host "$Name is already starting; waiting for readiness."
        return
    }

    # WMI owns the launcher, so a temporary calling terminal cannot take it down.
    $startup = New-CimInstance -CimClass (Get-CimClass Win32_ProcessStartup) -ClientOnly
    $startup.ShowWindow = 0
    $log = Join-Path $bencaoLogs ($Name + '.log')
    $command = '"' + $env:ComSpec + '" /d /s /c ""' + $launcherPath + '" > "' + $log + '" 2>&1 <nul"'
    $started = Invoke-CimMethod -ClassName Win32_Process -MethodName Create -Arguments @{
        CommandLine = $command
        CurrentDirectory = $bencaoRoot
        ProcessStartupInformation = $startup
    }
    if ($started.ReturnValue -ne 0) {
        throw "Cannot start $Name (Windows error $($started.ReturnValue)). See $log"
    }
    Write-Host "Started $Name launcher (PID $($started.ProcessId)). Log: $log"
}

if ($Check) {
    $backendReady = Test-BencaoEndpoint 'http://127.0.0.1:8000/api/health' 'bencao-api'
    $frontendReady = Test-BencaoEndpoint 'http://127.0.0.1:3000/login' ([string][char]0x767b + [char]0x5f55)
    $proxyReady = Test-BencaoEndpoint 'http://127.0.0.1:3000/api/health' 'bencao-api'
    Write-Host "Backend ready: $backendReady; login ready: $frontendReady; API proxy ready: $proxyReady"
    if ($backendReady -and $frontendReady -and $proxyReady) { exit 0 }
    exit 1
}

$hashAlgorithm = [System.Security.Cryptography.SHA256]::Create()
try {
    $rootHash = [BitConverter]::ToString($hashAlgorithm.ComputeHash([Text.Encoding]::UTF8.GetBytes($bencaoRoot.ToUpperInvariant()))).Replace('-', '')
} finally { $hashAlgorithm.Dispose() }
$startupMutex = New-Object System.Threading.Mutex($false, ('Local\BencaoStartup-' + $rootHash))
$ownsMutex = $false
try {
    try { $ownsMutex = $startupMutex.WaitOne(0) } catch [System.Threading.AbandonedMutexException] { $ownsMutex = $true }
    if (-not $ownsMutex) {
        Write-Host 'Another Bencao launcher is waiting for startup. Please wait for its result.'
        exit 0
    }
    if (-not (Test-Path -LiteralPath (Join-Path $bencaoRoot 'backend\.venv\Scripts\python.exe')) -or
        -not (Test-Path -LiteralPath (Join-Path $bencaoRoot 'frontend\node_modules\next\dist\bin\next'))) {
        throw 'First install: run the existing backend and frontend launchers interactively to install dependencies and create the administrator.'
    }
    New-Item -ItemType Directory -Path $bencaoLogs -Force | Out-Null
    # Resolve the existing Unicode launcher names without depending on PS 5.1 file encoding.
    $backendLauncher = [string][char]0x542f + [char]0x52a8 + [char]0x540e + [char]0x7aef + '.cmd'
    $frontendLauncher = [string][char]0x542f + [char]0x52a8 + [char]0x524d + [char]0x7aef + '.cmd'
    Start-BencaoService 'backend' $backendLauncher 'http://127.0.0.1:8000/api/health' 'bencao-api'
    Start-BencaoService 'frontend' $frontendLauncher 'http://127.0.0.1:3000/login' ([string][char]0x767b + [char]0x5f55)
    Write-Host 'Waiting for both services. Local model warmup can take 1-3 minutes.'
    $deadline = [DateTime]::UtcNow.AddSeconds($TimeoutSeconds)
    do {
        $backendReady = Test-BencaoEndpoint 'http://127.0.0.1:8000/api/health' 'bencao-api'
        $frontendReady = Test-BencaoEndpoint 'http://127.0.0.1:3000/login' ([string][char]0x767b + [char]0x5f55)
        if ($backendReady -and $frontendReady -and (Test-BencaoEndpoint 'http://127.0.0.1:3000/api/health' 'bencao-api')) {
            Write-Host 'Bencao is ready: http://127.0.0.1:3000/'
            Write-Host 'Services run independently. You may close this launcher window.'
            exit 0
        }
        Start-Sleep -Seconds 2
    } while ([DateTime]::UtcNow -lt $deadline)
    throw "Startup did not become ready in $TimeoutSeconds seconds. Check $bencaoLogs\backend.log and frontend.log; services may still be warming up."
} catch {
    Write-Host $_.Exception.Message -ForegroundColor Red
    exit 1
} finally {
    if ($ownsMutex) { $startupMutex.ReleaseMutex() }
    $startupMutex.Dispose()
}
