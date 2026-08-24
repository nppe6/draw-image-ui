$ErrorActionPreference = "Stop"

$skillDir = Split-Path -Parent $PSScriptRoot
$wrapper = Join-Path $skillDir "scripts\ask_draw.ps1"
$testDir = Join-Path $env:TEMP ("draw-image-ui-wrapper-" + [guid]::NewGuid().ToString("N"))
$fakePython = Join-Path $testDir "fake-python.ps1"
$capturedArgs = Join-Path $testDir "args.txt"
$outputPath = Join-Path $testDir "result.png"
$framePath = Join-Path $testDir "frame.png"

try {
    New-Item -ItemType Directory -Path $testDir | Out-Null

    @'
param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]] $Captured
)

$Captured | Set-Content -LiteralPath $env:DRAW_TEST_ARGS -Encoding UTF8
'@ | Set-Content -LiteralPath $fakePython -Encoding UTF8

    $env:DRAW_PYTHON = $fakePython
    $env:DRAW_TEST_ARGS = $capturedArgs

    & $wrapper -o $outputPath --frame $framePath --provider codex --help
    if ($LASTEXITCODE -ne 0) {
        throw "ask_draw.ps1 exited with code $LASTEXITCODE"
    }

    $actual = @(Get-Content -LiteralPath $capturedArgs)
    $expected = @(
        (Join-Path $skillDir "scripts\generate_image.py"),
        "--ref",
        $framePath,
        "--output",
        $outputPath,
        "--provider",
        "codex",
        "--help"
    )

    if ($actual.Count -ne $expected.Count) {
        throw "Expected $($expected.Count) arguments, got $($actual.Count): $($actual -join ' | ')"
    }

    for ($i = 0; $i -lt $expected.Count; $i++) {
        if ($actual[$i] -ne $expected[$i]) {
            throw "Argument $i mismatch. Expected '$($expected[$i])', got '$($actual[$i])'"
        }
    }

    Write-Output "ask_draw.ps1 wrapper test passed"
}
finally {
    Remove-Item Env:DRAW_PYTHON -ErrorAction SilentlyContinue
    Remove-Item Env:DRAW_TEST_ARGS -ErrorAction SilentlyContinue
    if (Test-Path -LiteralPath $testDir) {
        Remove-Item -LiteralPath $testDir -Recurse -Force
    }
}
