param(
    [string]$SourceRoot = "D:\Project\MIA-lihao\IAplusBigLLM"
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot

Push-Location $ProjectRoot
try {
    & conda run -n rag_env python -m rag_mia_data.cli dataset-import --source-root $SourceRoot
    if ($LASTEXITCODE -ne 0) {
        throw "dataset-import failed with exit code $LASTEXITCODE"
    }

    & conda run -n rag_env python -m rag_mia_data.cli dataset-normalize --mode all
    if ($LASTEXITCODE -ne 0) {
        throw "dataset-normalize failed with exit code $LASTEXITCODE"
    }

    & conda run -n rag_env python -m rag_mia_data.cli dataset-validate --mode all
    if ($LASTEXITCODE -ne 0) {
        throw "dataset-validate failed with exit code $LASTEXITCODE"
    }
}
finally {
    Pop-Location
}
