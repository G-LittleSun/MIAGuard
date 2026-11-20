param(
    [string]$OutputRunId = "20260725-ag-news-query-bank-10x10-v1",
    [string]$QueryBankId = "ag_news_queries_v1",
    [int]$QuerySeed = 20260725
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$LogDirectory = Join-Path $ProjectRoot "data\experiment_logs"
$LogPath = Join-Path $LogDirectory "$OutputRunId.log"
New-Item -ItemType Directory -Force -Path $LogDirectory | Out-Null

function Write-ExperimentLog {
    param([string]$Message)
    $Line = "[$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] $Message"
    Write-Host $Line
    Add-Content -LiteralPath $LogPath -Value $Line -Encoding UTF8
}

Set-Location $ProjectRoot
$Env:HF_HUB_DISABLE_PROGRESS_BARS = "1"
$Env:TRANSFORMERS_NO_ADVISORY_WARNINGS = "1"
$Env:TQDM_DISABLE = "1"
$CondaExe = $Env:CONDA_EXE
if (-not $CondaExe -or -not (Test-Path -LiteralPath $CondaExe)) {
    $CondaCommand = Get-Command conda.exe -ErrorAction Stop
    $CondaExe = $CondaCommand.Source
}

Set-Content -LiteralPath $LogPath -Value "" -Encoding UTF8
Write-ExperimentLog "Starting MIAGuard 10+10 experiment"
Write-ExperimentLog "Conda executable: $CondaExe"
Write-ExperimentLog "Environment: MIAGuard"
Write-ExperimentLog "Dataset: ag_news; four attacks: 10 members + 10 nonmembers each; benign: 20; IA turns: 3"
Write-ExperimentLog "Output run id: $OutputRunId"
Write-ExperimentLog "Live progress fields: stage1_mean, stage2_mean, total_mean, access level, access action"

$ErrorActionPreference = "Continue"
& $CondaExe run --no-capture-output -n MIAGuard python -u scripts/run_two_stage_attack_comparison.py `
    --config configs/attacks/ag_news_calibrated_int8.yaml `
    --gateway-config configs/defense/two_stage_direct_enforce_calibrated_010.yaml `
    --source-run-id 20260717-ag-news-four-medium `
    --dataset ag_news `
    --output-run-id $OutputRunId `
    --limit-per-class 10 `
    --benign-count 20 `
    --ia-turn-count 3 `
    --query-bank-id $QueryBankId `
    --query-seed $QuerySeed `
    --variant-mode canonical `
    --project-root $ProjectRoot 2>&1 | ForEach-Object {
        $Line = $_.ToString()
        Write-Host $Line
        Add-Content -LiteralPath $LogPath -Value $Line -Encoding UTF8
    }

$ExitCode = $LASTEXITCODE
$ErrorActionPreference = "Stop"
if ($ExitCode -ne 0) {
    Write-ExperimentLog "Experiment failed with exit code $ExitCode"
    Write-ExperimentLog "Inspect the error above in: $LogPath"
    exit $ExitCode
}

Write-ExperimentLog "Experiment completed successfully"
Write-ExperimentLog "Results: data\two_stage_attack_results\$OutputRunId\ag_news"
