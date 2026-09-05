$ErrorActionPreference = 'Stop'

$dllCandidates = @(
    (Join-Path $PSScriptRoot 'csharp\bin\x64\Release\net48\CompasAiCad.dll'),
    (Join-Path $PSScriptRoot 'csharp\bin\Release\CompasAiCad.dll')
)
$dll = $dllCandidates | Where-Object { Test-Path $_ } | Select-Object -First 1
$regasm = Join-Path $env:WINDIR 'Microsoft.NET\Framework64\v4.0.30319\RegAsm.exe'

if ((Test-Path $dll) -and (Test-Path $regasm)) {
    & $regasm $dll /unregister | Out-Host
}

Remove-Item 'HKCU:\Software\ASCON\KOMPAS-3D\AddIns\CompasAiCad' -Recurse -Force -ErrorAction SilentlyContinue

Write-Host 'AI CAD AddIn removed.' -ForegroundColor Green
