$ErrorActionPreference = 'Stop'
$src = 'd:\resume-upup\resume-matcher-agent-cn\a4cv-main'
$dst = 'd:\resume-upup\resume-matcher-agent-cn\apps\frontend\public\a4cv'

# 清理可能的不完整目录
if (Test-Path $dst) { Remove-Item -Recurse -Force $dst }
New-Item -ItemType Directory -Force -Path $dst | Out-Null

# vendor
$vdst = Join-Path $dst 'vendor'
New-Item -ItemType Directory -Force -Path $vdst | Out-Null
Get-ChildItem -Path (Join-Path $src 'vendor') -File | ForEach-Object {
    Copy-Item -Path $_.FullName -Destination $vdst -Force
}

# assets
$adst = Join-Path $dst 'assets'
New-Item -ItemType Directory -Force -Path $adst | Out-Null
Get-ChildItem -Path (Join-Path $src 'assets') -File | ForEach-Object {
    Copy-Item -Path $_.FullName -Destination $adst -Force
}

# index.html
Copy-Item -Path (Join-Path $src 'index.html') -Destination $dst -Force

Write-Output "=== DONE ==="
Get-ChildItem -Path $dst -Recurse -File | ForEach-Object {
    $rel = $_.FullName.Substring($dst.Length)
    Write-Output ("{0,8} KB  {1}" -f [math]::Round($_.Length/1KB,1), $rel)
}
