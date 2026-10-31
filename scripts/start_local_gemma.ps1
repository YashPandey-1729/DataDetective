param([switch]$Pull)
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$runtimeRoot = Join-Path $projectRoot 'runtime'
$portableOllama = Join-Path $runtimeRoot 'ollama\ollama.exe'
$installedOllama = Get-Command ollama -ErrorAction SilentlyContinue
$ollamaExecutable = if (Test-Path -LiteralPath $portableOllama) { $portableOllama } elseif ($installedOllama) { $installedOllama.Source } else { throw 'Install Ollama from https://ollama.com/download/windows, then run this script again.' }
New-Item -ItemType Directory -Force -Path $runtimeRoot | Out-Null
# These settings affect only this PowerShell session and its child processes.
$env:OLLAMA_HOST = '127.0.0.1:11434'
$env:OLLAMA_NO_CLOUD = '1'
$env:OLLAMA_NUM_PARALLEL = '1'
if ($ollamaExecutable -eq $portableOllama) { $env:OLLAMA_MODELS = Join-Path $runtimeRoot 'models' }
try { $null = Invoke-RestMethod 'http://127.0.0.1:11434/api/tags' -TimeoutSec 2 }
catch {
    Start-Process -FilePath $ollamaExecutable -ArgumentList 'serve' -WorkingDirectory $projectRoot -WindowStyle Hidden -RedirectStandardOutput (Join-Path $runtimeRoot 'ollama.stdout.log') -RedirectStandardError (Join-Path $runtimeRoot 'ollama.stderr.log') | Out-Null
    $ready = $false
    for ($attempt=0; $attempt -lt 20; $attempt++) {
        Start-Sleep -Milliseconds 500
        try { $null = Invoke-RestMethod 'http://127.0.0.1:11434/api/tags' -TimeoutSec 1; $ready = $true; break } catch {}
    }
    if (-not $ready) { throw 'Ollama did not start. Check runtime\ollama.stderr.log.' }
}
if ($Pull) {
    $model = if ($env:OLLAMA_MODEL) { $env:OLLAMA_MODEL } else { 'gemma4:e4b' }
    if ($model -notmatch '^gemma4:[A-Za-z0-9_.-]+$' -or $model -match 'cloud') { throw 'Choose a local gemma4 tag, without a cloud suffix.' }
    & $ollamaExecutable pull $model
    if ($LASTEXITCODE -ne 0) { throw 'Local Gemma download failed.' }
}
Write-Output 'Local Ollama is available at http://127.0.0.1:11434. Reconnect DataDetective and select Gemma 4 · Local (Ollama).'
