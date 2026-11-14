param([string]$Compiler=$env:CXX)
$ErrorActionPreference='Stop'
if(!$Compiler){$Compiler='g++'}
$base=Split-Path $PSScriptRoot
$deps=Join-Path $base '../../population_motion_research_20261106'
$flags=@('-std=c++17','-O3','-DNDEBUG','-DEAAI_ARM_OVERTRAVEL','-DEAAI_SWEEP','-static','-I',(Join-Path $deps 'third_party/eigen3'))
foreach($entry in @('docking','shared','shoot_dock','shoot_shared')){
  $binary=if($entry -eq 'docking'){'dock'}else{$entry}
  $files=@((Join-Path $base "src/$entry.cpp"))
  & $Compiler @flags @files -o (Join-Path $PSScriptRoot "$binary.exe")
  if($LASTEXITCODE){throw "Cannot compile $entry"}
}
$info=@{compiler=(& $Compiler --version | Select-Object -First 1);flags=$flags;platform='Windows x64'}
$info | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath (Join-Path $PSScriptRoot 'build_info.json') -Encoding utf8
