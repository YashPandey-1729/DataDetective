param([switch]$Check)
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$pythonPath = Join-Path $projectRoot '.venv\Scripts\python.exe'
$vitePath = Join-Path $projectRoot 'frontend\node_modules\vite\bin\vite.js'
$nodeCommand = Get-Command node -ErrorAction SilentlyContinue
if (-not (Test-Path -LiteralPath $pythonPath)) { throw 'Python environment missing. Install dependencies using the README first. This launcher does not download packages.' }
if (-not $nodeCommand -or -not (Test-Path -LiteralPath $vitePath)) { throw 'Node or frontend dependencies missing. Follow the README installation steps first. No downloads were started.' }
if ($Check) { Write-Output 'Installed Python, Node and Vite found. No downloads or services started.'; exit 0 }
$runtimeRoot = Join-Path $projectRoot 'runtime'
New-Item -ItemType Directory -Force -Path $runtimeRoot | Out-Null
$backendProcess = $null
$frontendProcess = $null
function Test-Backend {
    try {
        $schema = Invoke-RestMethod 'http://127.0.0.1:8000/openapi.json' -TimeoutSec 3
        $health = Invoke-RestMethod 'http://127.0.0.1:8000/api/health' -TimeoutSec 3
        return ($schema.info.title -eq 'DataDetective AI' -and $health.status -eq 'ok')
    } catch { return $false }
}
function Test-Frontend {
    try {
        $page = Invoke-WebRequest 'http://127.0.0.1:5173/' -UseBasicParsing -TimeoutSec 3
        return ($page.StatusCode -eq 200 -and $page.Content -match '<title>DataDetective AI')
    } catch { return $false }
}
function Assert-PortFree([int]$Port) {
    $listener = [System.Net.Sockets.TcpListener]::new([System.Net.IPAddress]::Loopback, $Port)
    try { $listener.Start() }
    catch { throw "Port $Port is occupied or unavailable, and no healthy DataDetective service was found there. Close the old server's terminal with Ctrl+C, then run this launcher again." }
    finally { $listener.Stop() }
}
try {
    $reuseBackend = Test-Backend
    $reuseFrontend = Test-Frontend
    if (-not $reuseBackend) { Assert-PortFree 8000 }
    if (-not $reuseFrontend) { Assert-PortFree 5173 }
    if ($reuseBackend) { Write-Output 'Reusing DataDetective backend on port 8000. Restart its original terminal if you changed backend code.' }
    else {
    $backendArgs = @('-m','uvicorn','backend.main:app','--app-dir',('"'+$projectRoot+'"'),'--host','127.0.0.1','--port','8000')
    $backendProcess = Start-Process -FilePath $pythonPath -ArgumentList $backendArgs -WorkingDirectory $projectRoot -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $runtimeRoot 'backend.stdout.log') -RedirectStandardError (Join-Path $runtimeRoot 'backend.stderr.log')
    }
    if ($reuseFrontend) { Write-Output 'Reusing DataDetective frontend on port 5173.' }
    else {
    $frontendArgs = @(('"'+$vitePath+'"'),'--host','127.0.0.1','--port','5173','--strictPort')
    $frontendProcess = Start-Process -FilePath $nodeCommand.Source -ArgumentList $frontendArgs -WorkingDirectory (Join-Path $projectRoot 'frontend') -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $runtimeRoot 'frontend.stdout.log') -RedirectStandardError (Join-Path $runtimeRoot 'frontend.stderr.log')
    }
    $ready = $false
    for ($attempt = 0; $attempt -lt 30; $attempt++) {
        if (($backendProcess -and $backendProcess.HasExited) -or ($frontendProcess -and $frontendProcess.HasExited)) { throw 'A server stopped. Check runtime\backend.stderr.log and runtime\frontend.stderr.log. Another instance may have taken the port.' }
        try {
            $health = Invoke-RestMethod 'http://127.0.0.1:8000/api/health' -TimeoutSec 2
            $page = Invoke-WebRequest 'http://127.0.0.1:5173/' -UseBasicParsing -TimeoutSec 2
            if ($health.status -eq 'ok' -and $page.StatusCode -eq 200) { $ready = $true; break }
        } catch { Start-Sleep -Milliseconds 500 }
    }
    if (-not $ready) { throw 'The app did not become ready. Check the runtime server logs.' }
    Write-Output 'DataDetective is ready: http://127.0.0.1:5173'
    if (-not $backendProcess -and -not $frontendProcess) { Write-Output 'Both services were already running; no new processes started.'; return }
    Write-Output 'Keep this terminal open. Ctrl+C stops only servers started by this launcher; reused servers stay running.'
    Write-Output 'Offline analytics and the statistics workbench work without an AI key or model download.'
    while ((-not $backendProcess -or -not $backendProcess.HasExited) -and (-not $frontendProcess -or -not $frontendProcess.HasExited)) { Start-Sleep -Seconds 1 }
    throw 'A server stopped. Check the runtime server logs.'
} finally {
    foreach ($ownedProcess in @($frontendProcess,$backendProcess)) {
        if ($ownedProcess -and -not $ownedProcess.HasExited) { Stop-Process -Id $ownedProcess.Id -ErrorAction SilentlyContinue }
    }
}
