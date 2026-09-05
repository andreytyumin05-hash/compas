$ErrorActionPreference = 'Stop'

$dll = Join-Path $PSScriptRoot 'csharp\bin\Release\CompasAiCad.dll'
$regasm = Join-Path $env:WINDIR 'Microsoft.NET\Framework64\v4.0.30319\RegAsm.exe'

if ((Test-Path $dll) -and (Test-Path $regasm)) {
    & $regasm $dll /unregister | Out-Host
}

Remove-Item 'HKCU:\Software\ASCON\KOMPAS-3D\AddIns\CompasAiCad' -Recurse -Force -ErrorAction SilentlyContinue

Write-Host 'AI CAD AddIn удалён.' -ForegroundColor Green
