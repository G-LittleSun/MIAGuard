param(
    [int]$Workers = 16,
    [int]$ChunkMb = 128
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$python = "D:\ProgramData\Anaconda3\envs\MIAGuard\python.exe"
$models = @("mistral_7b", "gpt2_xl", "glm4_9b", "phi4_14b", "qwen2_5_14b_1m")

if (-not (Test-Path -LiteralPath $python -PathType Leaf)) {
    throw "MIAGuard Python executable not found: $python"
}

Push-Location $root
try {
    foreach ($model in $models) {
        Write-Output "DOWNLOAD_START $model $(Get-Date -Format o)"
        & $python scripts\download_hf_weights_chunked.py `
            --model $model `
            --workers $Workers `
            --chunk-mb $ChunkMb
        if ($LASTEXITCODE -ne 0) {
            throw "Download failed for $model with exit code $LASTEXITCODE"
        }
        Write-Output "VERIFY_START $model $(Get-Date -Format o)"
        & $python scripts\verify_teacher_model.py --model $model
        if ($LASTEXITCODE -ne 0) {
            throw "Verification failed for $model with exit code $LASTEXITCODE"
        }
        Write-Output "MODEL_COMPLETE $model $(Get-Date -Format o)"
    }
    & $python scripts\audit_teacher_models.py
    Write-Output "PUBLIC_MODELS_COMPLETE $(Get-Date -Format o)"
}
finally {
    Pop-Location
}
