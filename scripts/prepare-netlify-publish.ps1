[CmdletBinding()]
param(
    [string]$OutputDirectory,
    [switch]$Clean
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

if ([string]::IsNullOrWhiteSpace($OutputDirectory)) {
    $OutputDirectory = Join-Path -Path $PSScriptRoot -ChildPath '..\dist'
}

$repositoryRoot = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$outputPath = [System.IO.Path]::GetFullPath($OutputDirectory)
$rootPrefix = $repositoryRoot.TrimEnd([System.IO.Path]::DirectorySeparatorChar) + [System.IO.Path]::DirectorySeparatorChar

if ($outputPath -eq $repositoryRoot -or -not $outputPath.StartsWith($rootPrefix, [System.StringComparison]::OrdinalIgnoreCase)) {
    throw "OutputDirectory must be inside the repository and cannot be the repository root: $outputPath"
}

$htmlPages = @(
    'index.html',
    'accounting-management.html',
    'forensic-services.html',
    'tax-advisory-compliance.html',
    'corporate-secretarial.html',
    'corporate-advisory.html',
    'training.html',
    'payroll-services.html',
    'corporate-finance.html'
)
$rootFiles = @('sitemap.xml', 'robots.txt', '_headers')
$assetExtensions = @('.css', '.js', '.jpg', '.jpeg', '.png', '.webp', '.gif', '.svg', '.ico', '.avif', '.woff', '.woff2')

foreach ($file in $htmlPages + $rootFiles) {
    if (-not (Test-Path -LiteralPath (Join-Path $repositoryRoot $file) -PathType Leaf)) {
        throw "Required publish file is missing: $file"
    }
}

if (Test-Path -LiteralPath $outputPath) {
    if (-not $Clean -and (Get-ChildItem -LiteralPath $outputPath -Force | Select-Object -First 1)) {
        throw "Output directory is not empty. Review it, then rerun with -Clean only if you intend to replace this exact dist directory: $outputPath"
    }
    if ($Clean) {
        Remove-Item -LiteralPath $outputPath -Recurse -Force
    }
}

New-Item -ItemType Directory -Path $outputPath -Force | Out-Null
New-Item -ItemType Directory -Path (Join-Path $outputPath 'assets') -Force | Out-Null

foreach ($file in $htmlPages + $rootFiles) {
    Copy-Item -LiteralPath (Join-Path $repositoryRoot $file) -Destination (Join-Path $outputPath $file) -Force
}

Get-ChildItem -LiteralPath (Join-Path $repositoryRoot 'assets') -File |
    Where-Object { $assetExtensions -contains $_.Extension.ToLowerInvariant() } |
    ForEach-Object { Copy-Item -LiteralPath $_.FullName -Destination (Join-Path $outputPath 'assets') -Force }

$forbidden = Get-ChildItem -LiteralPath $outputPath -Recurse -Force -File |
    Where-Object { $_.Name -match '(^|\.)(pdf|md|py|ps1|log)$' -or $_.FullName -match '\\(\.git|docs|scripts|\.netlify)(\\|$)' }
if ($forbidden) {
    throw "Forbidden development/source files were copied into the publish directory: $($forbidden.FullName -join ', ')"
}

$publishedFiles = Get-ChildItem -LiteralPath $outputPath -Recurse -Force -File |
    ForEach-Object { $_.FullName.Substring($outputPath.Length + 1) } |
    Sort-Object
Write-Output "Prepared Netlify publish directory: $outputPath"
$publishedFiles | ForEach-Object { Write-Output " - $_" }
