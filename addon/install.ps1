$ErrorActionPreference = 'Stop'

$repo = $env:COMPAS_REPO
if ([string]::IsNullOrWhiteSpace($repo)) {
    $repo = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
}
$repo = (Resolve-Path $repo).Path

$python = $env:COMPAS_PYTHON
if ([string]::IsNullOrWhiteSpace($python)) {
    $cmd = Get-Command python.exe -ErrorAction SilentlyContinue
    if ($cmd) { $python = $cmd.Source }
}
if ([string]::IsNullOrWhiteSpace($python)) {
    throw 'python.exe not found. Activate Python or set COMPAS_PYTHON.'
}

$csproj = Join-Path $PSScriptRoot 'csharp\CompasAiCad.csproj'
$msbuild = $null
$vswhere = Join-Path ${env:ProgramFiles(x86)} 'Microsoft Visual Studio\Installer\vswhere.exe'
if (Test-Path $vswhere) {
    $msbuild = & $vswhere -latest -products * -requires Microsoft.Component.MSBuild -find 'MSBuild\**\Bin\MSBuild.exe' | Select-Object -First 1
}
if ([string]::IsNullOrWhiteSpace($msbuild)) {
    $cmd = Get-Command msbuild.exe -ErrorAction SilentlyContinue
    if ($cmd) { $msbuild = $cmd.Source }
}
if ([string]::IsNullOrWhiteSpace($msbuild)) {
    throw 'MSBuild not found. Install Visual Studio 2022 with .NET desktop development workload.'
}

Write-Host "[1/4] Building $csproj"
& $msbuild $csproj /t:Build /p:Configuration=Release /p:Platform=x64 /m
if ($LASTEXITCODE -ne 0) { throw "MSBuild failed with exit code $LASTEXITCODE" }

$dll = Join-Path $PSScriptRoot 'csharp\bin\Release\CompasAiCad.dll'
if (-not (Test-Path $dll)) { throw "Build output not found: $dll" }

$regasm = Join-Path $env:WINDIR 'Microsoft.NET\Framework64\v4.0.30319\RegAsm.exe'
if (-not (Test-Path $regasm)) { throw "x64 RegAsm not found: $regasm" }

Write-Host '[2/4] Registering COM class'
& $regasm $dll /codebase /tlb
if ($LASTEXITCODE -ne 0) { throw "RegAsm failed with exit code $LASTEXITCODE" }

Write-Host '[3/4] Registering KOMPAS AddIn'
$addin = 'HKCU:\Software\ASCON\KOMPAS-3D\AddIns\CompasAiCad'
New-Item -Path $addin -Force | Out-Null
Set-ItemProperty -Path $addin -Name 'ProgID' -Value 'CompasAiCad.Panel' -Type String
Set-ItemProperty -Path $addin -Name 'Path' -Value $dll -Type String
Set-ItemProperty -Path $addin -Name 'AutoConnect' -Value 1 -Type DWord

Write-Host '[4/4] Saving runtime paths'
[Environment]::SetEnvironmentVariable('COMPAS_REPO', $repo, 'User')
[Environment]::SetEnvironmentVariable('COMPAS_PYTHON', $python, 'User')

Write-Host ''
Write-Host 'AI CAD AddIn installed successfully.' -ForegroundColor Green
Write-Host "DLL:    $dll"
Write-Host "Repo:   $repo"
Write-Host "Python: $python"
Write-Host 'Restart KOMPAS-3D. The AI CAD panel should be available from the AddIns/Libraries area.'
