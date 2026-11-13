$ErrorActionPreference = 'Continue'
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$env:HTTPS_PROXY = 'http://127.0.0.1:7890'
$env:HTTP_PROXY = 'http://127.0.0.1:7890'
& 'D:\PyCharm\Python\python.exe' -m pip install --disable-pip-version-check flask 2>&1 | ForEach-Object { Write-Output $_ }
Write-Output ('pip rc=' + $LASTEXITCODE)
& 'D:\PyCharm\Python\python.exe' -c "import flask; print('flask', flask.__version__)" 2>&1 | ForEach-Object { Write-Output $_ }
Write-Output ('import rc=' + $LASTEXITCODE)
