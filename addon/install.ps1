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
    throw 'python.exe не найден. Установите/активируйте Python или задайте COMPAS_PYTHON.'
}

$csproj = Join-Path $PSScriptRoot 'csharp\CompasAiCad.csproj'
$msbuild = $null
$vswhere = Join-Path ${env:ProgramFiles(x86)} 'Microsoft Visual Studio\Installer\vswhere.exe'
if (Test-Path $vswhere) {
    $msbuild = & $vswhere -latest -products * -requires Microsoft.Component.MSBuild -find MSBuild\**\Bin\MSBuild.exe | Select-Object -First 1
}
if ([string]::IsNullOrWhiteSpace($msbuild)) {
    $msbuild = Get-Command msbuild.exe -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Source
}
if ([string]::IsNullOrWhiteSpace($msbuild)) {
    throw 'MSBuild не найден. Установите Visual Studio 2022 с workload .NET desktop development.'
}

Write-Host "[1/4] Build: $csproj"
& $msbuild $csproj /t:Build /p:Configuration=Release /p:Platform=x64 /m
if ($LASTEXITCODE -ne 0) { throw "MSBuild завершился с кодом $LASTEXITCODE" }

$dll = Join-Path $PSScriptRoot 'csharp\bin\Release\CompasAiCad.dll'
if (-not (Test-Path $dll)) { throw "Не найден результат сборки: $dll" }

$regasm = Join-Path $env:WINDIR 'Microsoft.NET\Framework64\v4.0.30319\RegAsm.exe'
if (-not (Test-Path $regasm)) { throw "Не найден RegAsm x64: $regasm" }

Write-Host '[2/4] Register COM class'
& $regasm $dll /codebase /tlb
if ($LASTEXITCODE -ne 0) { throw "RegAsm завершился с кодом $LASTEXITCODE" }

Write-Host '[3/4] Register KOMPAS AddIn'
$addin = 'HKCU:\Software\ASCON\KOMPAS-3D\AddIns\CompasAiCad'
New-Item -Path $addin -Force | Out-Null
Set-ItemProperty -Path $addin -Name 'ProgID' -Value 'CompasAiCad.Panel' -Type String
Set-ItemProperty -Path $addin -Name 'Path' -Value $dll -Type String
Set-ItemProperty -Path $addin -Name 'AutoConnect' -Value 1 -Type DWord

Write-Host '[4/4] Persist runtime paths'
[Environment]::SetEnvironmentVariable('COMPAS_REPO', $repo, 'User')
[Environment]::SetEnvironmentVariable('COMPAS_PYTHON', $python, 'User')

Write-Host ''
Write-Host 'AI CAD AddIn установлен.' -ForegroundColor Green
Write-Host "DLL:    $dll"
Write-Host "Repo:   $repo"
Write-Host "Python: $python"
Write-Host 'Перезапустите КОМПАС-3D. В меню Библиотеки появится «Панель AI CAD».'
