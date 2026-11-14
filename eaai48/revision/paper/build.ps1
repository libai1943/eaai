param([string]$Tectonic=$env:TECTONIC,[switch]$FetchBundle)
if(!$Tectonic){$Tectonic='tectonic'}
$ErrorActionPreference='Stop';$base=Split-Path $PSScriptRoot
$stage=Join-Path $base 'tmp/typeset';$dest=Join-Path $base 'output/pdf'
New-Item -ItemType Directory -Force -Path $stage,$dest|Out-Null
[string[]]$opts=@();if(!$FetchBundle){$opts=@('--only-cached')}
Push-Location $PSScriptRoot
try{& $Tectonic @opts --keep-logs --outdir $stage manuscript.tex *> (Join-Path $stage 'build.log')
 if($LASTEXITCODE){throw "See $stage/build.log"}
 Copy-Item -LiteralPath (Join-Path $stage 'manuscript.pdf') -Destination (Join-Path $dest 'RegionCovOpt_EAAI.pdf') -Force
}finally{Pop-Location}

