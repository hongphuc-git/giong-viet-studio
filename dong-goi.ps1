$ErrorActionPreference = 'Stop'
$sourceRoot = $PSScriptRoot
$projectRoot = Split-Path $sourceRoot -Parent
$packageRoot = Join-Path $sourceRoot 'Giong-Viet-Portable'
$environmentPython = Join-Path $projectRoot '.tools/vieneu/Scripts/python.exe'
New-Item -ItemType Directory -Force -Path $packageRoot | Out-Null
foreach ($directory in @('runtime', 'models', 'bin', 'voices', 'web', 'source', 'outputs', 'work', 'logs')) {
    New-Item -ItemType Directory -Force -Path (Join-Path $packageRoot $directory) | Out-Null
}
$pythonArchive = Join-Path $sourceRoot 'python-3.13.9-embed-amd64.zip'
if (-not (Test-Path -LiteralPath $pythonArchive)) {
    Invoke-WebRequest 'https://www.python.org/ftp/python/3.13.9/python-3.13.9-embed-amd64.zip' -OutFile $pythonArchive
}
Expand-Archive -LiteralPath $pythonArchive -DestinationPath (Join-Path $packageRoot 'runtime') -Force
[IO.File]::WriteAllText((Join-Path $packageRoot 'runtime/python313._pth'), "python313.zip`n.`nLib/site-packages`nimport site`n", [Text.UTF8Encoding]::new($false))
$packageSource = Join-Path $projectRoot '.tools/vieneu/Lib/site-packages'
& robocopy $packageSource (Join-Path $packageRoot 'runtime/Lib/site-packages') /E /R:1 /W:1 /NFL /NDL /NJH /NJS /NP /XD __pycache__ pip pyinstaller PyInstaller _pyinstaller_hooks_contrib /XF '*.pyc'
if ($LASTEXITCODE -ge 8) { throw 'Không sao chép được thư viện Python.' }
& robocopy (Join-Path $projectRoot '.tools/vieneu-models') (Join-Path $packageRoot 'models') /E /R:1 /W:1 /NFL /NDL /NJH /NJS /NP /XD .locks /XF '*.lock' '.agent_harnesses.json'
if ($LASTEXITCODE -ge 8) { throw 'Không sao chép được mô hình.' }
Copy-Item -LiteralPath 'C:/ProgramData/chocolatey/lib/ffmpeg/tools/ffmpeg/bin/ffmpeg.exe' -Destination (Join-Path $packageRoot 'bin/ffmpeg.exe')
Copy-Item -LiteralPath 'C:/ProgramData/chocolatey/lib/ffmpeg/tools/ffmpeg/LICENSE' -Destination (Join-Path $packageRoot 'bin/FFMPEG-LICENSE.txt')
Copy-Item -LiteralPath (Join-Path $projectRoot 'Vidieo tuyên truyền/giong-Ha-Noi/MC-tham-chieu-5p82-giay.wav') -Destination (Join-Path $packageRoot 'voices/MC-mau.wav')
Copy-Item -LiteralPath (Join-Path $sourceRoot 'worker.py') -Destination $packageRoot
Copy-Item -LiteralPath (Join-Path $sourceRoot 'HUONG-DAN.txt') -Destination $packageRoot
Push-Location $sourceRoot
try {
    & npm run build
    if ($LASTEXITCODE -ne 0) { throw 'Đóng gói giao diện thất bại.' }
    Copy-Item -Path (Join-Path $sourceRoot 'dist/*') -Destination (Join-Path $packageRoot 'web') -Recurse -Force
    & $environmentPython -m PyInstaller --noconfirm --clean --onefile --name 'Giong-Viet-Studio' --distpath $packageRoot --workpath (Join-Path $sourceRoot 'build-exe') (Join-Path $sourceRoot 'launcher.py')
    if ($LASTEXITCODE -ne 0) { throw 'Đóng gói EXE thất bại.' }
} finally { Pop-Location }
foreach ($file in @('launcher.py','worker.py','dong-goi.ps1','package.json','package-lock.json','vite.config.ts','index.html','HUONG-DAN.txt')) {
    Copy-Item -LiteralPath (Join-Path $sourceRoot $file) -Destination (Join-Path $packageRoot 'source') -Force
}
Copy-Item -LiteralPath (Join-Path $sourceRoot 'src') -Destination (Join-Path $packageRoot 'source') -Recurse -Force
Write-Output "Đã đóng gói: $packageRoot"
Write-Output 'Chưa chạy ứng dụng, kiểm thử hoặc lint/format. Hãy kiểm tra theo HUONG-DAN.txt.'
