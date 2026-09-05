$ErrorActionPreference = 'Stop'

$dll = Join-Path $PSScriptRoot 'csharp\bin\x64\Release\net48\CompasAiCad.dll'
$regasm = Join-Path $env:WINDIR 'Microsoft.NET\Framework64\v4.0.30319\RegAsm.exe'

if ((Test-Path $dll) -and (Test-Path $regasm)) {
    & $regasm $dll /unregister | Out-Host
}

Remove-Item 'HKCU:\Software\ASCON\KOMPAS-3D\AddIns\CompasAiCad' -Recurse -Force -ErrorAction SilentlyContinue

[Environment]::SetEnvironmentVariable('COMPAS_REPO', $null, 'User')
[Environment]::SetEnvironmentVariable('COMPAS_PYTHON', $null, 'User')

Write-Host 'AI CAD AddIn removed.' -ForegroundColor Green
