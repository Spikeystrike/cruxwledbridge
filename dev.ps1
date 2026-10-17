[CmdletBinding()]
param(
    [ValidateSet('Setup', 'Check', 'Test', 'Run')]
    [string]$Action = 'Test',
    [string]$Python,
    [string]$Node,
    [ValidateRange(1, 65535)]
    [int]$Port = 8000
)

$ErrorActionPreference = 'Stop'
$projectRoot = $PSScriptRoot
$venvPython = Join-Path $projectRoot '.venv\Scripts\python.exe'
$bundledRuntime = Join-Path $env:USERPROFILE '.cache\codex-runtimes\codex-primary-runtime\dependencies'
$environmentNames = @('PATH', 'TEMP', 'TMP', 'PIP_CACHE_DIR', 'PIP_DISABLE_PIP_VERSION_CHECK', 'PYTHONUTF8', 'DATABASE_URL')
$savedEnvironment = @{}
foreach ($name in $environmentNames) {
    $savedEnvironment[$name] = [Environment]::GetEnvironmentVariable($name, 'Process')
}

function Invoke-ProjectPython {
    & $venvPython @args
    if ($LASTEXITCODE -ne 0) {
        throw "Project Python exited with code $LASTEXITCODE."
    }
}

Push-Location -LiteralPath $projectRoot
try {
    # Keep all development writes inside the project, including Python's temp files.
    $env:TEMP = Join-Path $projectRoot '.cache\tmp'
    $env:TMP = $env:TEMP
    $env:PIP_CACHE_DIR = Join-Path $projectRoot '.cache\pip'
    $env:PIP_DISABLE_PIP_VERSION_CHECK = '1'
    $env:PYTHONUTF8 = '1'
    New-Item -ItemType Directory -Force -Path $env:TEMP, $env:PIP_CACHE_DIR | Out-Null

    if ($Action -eq 'Setup') {
        if (-not (Test-Path -LiteralPath $venvPython)) {
            if (-not $Python) {
                $Python = Join-Path $bundledRuntime 'python\python.exe'
                if (-not (Test-Path -LiteralPath $Python)) {
                    $command = Get-Command python -CommandType Application -ErrorAction SilentlyContinue
                    if (-not $command -or $command.Source -like '*\WindowsApps\*') {
                        throw 'Python 3.12 was not found. Run .\dev.ps1 Setup -Python C:\path\to\python.exe.'
                    }
                    $Python = $command.Source
                }
            }
            & $Python -c "import sys; sys.exit(0 if sys.version_info[:2] == (3, 12) else 'Python 3.12 is required, matching the Docker image.')"
            if ($LASTEXITCODE -ne 0) { throw 'Select a working Python 3.12 installation with -Python.' }
            & $Python -m venv (Join-Path $projectRoot '.venv')
            if ($LASTEXITCODE -ne 0) { throw 'Could not create the project virtual environment.' }
        }
    }

    if (-not (Test-Path -LiteralPath $venvPython)) {
        throw 'Project environment is missing. Run .\dev.ps1 Setup first.'
    }
    Invoke-ProjectPython -c "import sys; sys.exit(0 if sys.version_info[:2] == (3, 12) else 'Recreate .venv with Python 3.12, matching the Docker image.')"

    switch ($Action) {
        'Setup' {
            Invoke-ProjectPython -m ensurepip --upgrade
            Invoke-ProjectPython -m pip install --quiet --retries 0 --timeout 30 -r requirements.txt -c requirements-dev.lock.txt
            Invoke-ProjectPython -m pip check
            if (-not (Test-Path -LiteralPath 'config\config.py')) {
                Copy-Item -LiteralPath 'config\config.example.py' -Destination 'config\config.py'
            }
            Write-Host 'Setup complete. Run .\dev.ps1 Test. Configure config/config.py before starting the bridge.'
        }
        'Check' {
            Invoke-ProjectPython -c "import sys, tempfile, fastapi, uvicorn, pydantic, requests, numpy, sqlalchemy; print('Python:', sys.version.split()[0]); print('Executable:', sys.executable); print('Temp:', tempfile.gettempdir()); print('Application imports: OK')"
            Invoke-ProjectPython -m pip check
        }
        'Test' {
            # The UI test would otherwise silently skip when Node is absent.
            if (-not $Node) {
                $Node = Join-Path $bundledRuntime 'node\bin\node.exe'
                if (-not (Test-Path -LiteralPath $Node)) {
                    $command = Get-Command node -CommandType Application -ErrorAction SilentlyContinue
                    if (-not $command) { throw 'Node.js is required for the UI tests. Supply its executable with -Node.' }
                    $Node = $command.Source
                }
            }
            $Node = (Resolve-Path -LiteralPath $Node).Path
            & $Node --version
            if ($LASTEXITCODE -ne 0) { throw 'Node.js could not be started.' }
            $env:PATH = "$(Split-Path -Parent $Node);$env:PATH"
            Invoke-ProjectPython -c "import faulthandler, unittest; faulthandler.dump_traceback_later(120, exit=True); unittest.main(module=None, argv=['unittest', 'discover', '-s', 'tests', '-q'])"
        }
        'Run' {
            if (-not (Test-Path -LiteralPath 'config\config.py')) {
                throw 'Run .\dev.ps1 Setup, then configure config/config.py before starting the bridge.'
            }
            # Use a separate local database instead of the Docker-only /code/db path.
            New-Item -ItemType Directory -Force -Path (Join-Path $projectRoot 'db') | Out-Null
            $databasePath = (Join-Path $projectRoot 'db\app.db').Replace('\', '/')
            $env:DATABASE_URL = "sqlite:///$databasePath"
            Invoke-ProjectPython -m uvicorn main:app --host 127.0.0.1 --port $Port --no-access-log
        }
    }
}
finally {
    Pop-Location
    foreach ($name in $environmentNames) {
        [Environment]::SetEnvironmentVariable($name, $savedEnvironment[$name], 'Process')
    }
}
