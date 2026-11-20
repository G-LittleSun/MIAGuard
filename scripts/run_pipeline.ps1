param(
    [string]$Config = "configs/smoke.yaml"
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
Push-Location $ProjectRoot
try {
    $env:PYTHONPATH = Join-Path $ProjectRoot "src"
    foreach ($Command in @("inspect", "preprocess", "split", "validate")) {
        & conda run -n rag_env python -m rag_mia_data.cli $Command --config $Config
        if ($LASTEXITCODE -ne 0) {
            throw "Pipeline stage '$Command' failed with exit code $LASTEXITCODE"
        }
    }
}
finally {
    Pop-Location
}

