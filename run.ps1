param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$ArgsList
)

$venvPython = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
$targetScript = Join-Path $PSScriptRoot "dev.py"

if (Test-Path $venvPython) {
    if ($ArgsList) {
        & $venvPython $targetScript @ArgsList
    } else {
        & $venvPython $targetScript
    }
} else {
    if ($ArgsList) {
        python $targetScript @ArgsList
    } else {
        python $targetScript
    }
}
