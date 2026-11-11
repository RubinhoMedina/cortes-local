$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
$env:MCP_TRANSPORT = 'stdio'
$keyFile = Join-Path $PSScriptRoot 'private/youtube-api-key.xml'
if (-not $env:YOUTUBE_API_KEY -and (Test-Path -LiteralPath $keyFile)) {
    $secureKey = Import-Clixml -LiteralPath $keyFile
    $env:YOUTUBE_API_KEY = [System.Net.NetworkCredential]::new('', $secureKey).Password
}
if (-not $env:YOUTUBE_API_KEY) {
    $env:YOUTUBE_API_KEY = [Environment]::GetEnvironmentVariable('YOUTUBE_API_KEY', 'User')
}
try {
    & 'C:\Users\Windows\AppData\Local\Microsoft\WinGet\Packages\OpenJS.NodeJS.LTS_Microsoft.Winget.Source_8wekyb3d8bbwe\node-v24.20.0-win-x64\node.exe' (Join-Path $PSScriptRoot 'dist/index.js')
    exit $LASTEXITCODE
} finally {
    Remove-Item Env:YOUTUBE_API_KEY -ErrorAction SilentlyContinue
}
