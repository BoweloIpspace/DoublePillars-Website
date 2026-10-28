[CmdletBinding()]
param(
    [string]$SourceDirectory,
    [string]$OutputDirectory,
    [string]$CanonicalBaseUrl,
    [switch]$UseExtensionlessUrls,
    [switch]$Clean
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$repositoryRoot = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
if ([string]::IsNullOrWhiteSpace($SourceDirectory)) {
    $SourceDirectory = Join-Path $repositoryRoot 'dist'
}
if ([string]::IsNullOrWhiteSpace($OutputDirectory)) {
    $OutputDirectory = Join-Path $repositoryRoot '.cloudflare-pages'
}

$sourcePath = [System.IO.Path]::GetFullPath($SourceDirectory)
$outputPath = [System.IO.Path]::GetFullPath($OutputDirectory)
$rootPrefix = $repositoryRoot.TrimEnd([System.IO.Path]::DirectorySeparatorChar) + [System.IO.Path]::DirectorySeparatorChar

if (-not $sourcePath.StartsWith($rootPrefix, [System.StringComparison]::OrdinalIgnoreCase) -or
    -not $outputPath.StartsWith($rootPrefix, [System.StringComparison]::OrdinalIgnoreCase)) {
    throw 'SourceDirectory and OutputDirectory must be inside the repository.'
}
if ($sourcePath -eq $outputPath) {
    throw 'OutputDirectory must be separate from the existing dist build; this script never overwrites dist.'
}
if (-not (Test-Path -LiteralPath $sourcePath -PathType Container)) {
    throw "Source directory does not exist: $sourcePath"
}
if ($UseExtensionlessUrls -and [string]::IsNullOrWhiteSpace($CanonicalBaseUrl)) {
    throw 'UseExtensionlessUrls requires an approved CanonicalBaseUrl.'
}
if (-not [string]::IsNullOrWhiteSpace($CanonicalBaseUrl) -and -not $UseExtensionlessUrls) {
    throw 'CanonicalBaseUrl requires UseExtensionlessUrls; otherwise Cloudflare Pages can redirect .html URLs away from the staged canonical URLs.'
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

foreach ($file in $htmlPages + $rootFiles) {
    if (-not (Test-Path -LiteralPath (Join-Path $sourcePath $file) -PathType Leaf)) {
        throw "Required file is missing from the existing dist build: $file"
    }
}

if (Test-Path -LiteralPath $outputPath) {
    if (-not $Clean -and (Get-ChildItem -LiteralPath $outputPath -Force | Select-Object -First 1)) {
        throw "Output directory is not empty. Rerun with -Clean only for this generated directory: $outputPath"
    }
    if ($Clean) {
        Remove-Item -LiteralPath $outputPath -Recurse -Force
    }
}

New-Item -ItemType Directory -Path $outputPath -Force | Out-Null
Get-ChildItem -LiteralPath $sourcePath -Force | Copy-Item -Destination $outputPath -Recurse -Force

$indexPath = Join-Path $outputPath 'index.html'
$index = Get-Content -LiteralPath $indexPath -Raw -Encoding UTF8
$index = [regex]::Replace($index, '\sdata-netlify="true"\snetlify-honeypot="bot-field"', '')
$index = $index.Replace('name="enquiry" method="POST"', 'name="enquiry" method="POST" action="/api/contact"')
$index = $index.Replace("fetch('/', {", "fetch('/api/contact', {")
$index = [regex]::Replace($index, '\s*<input type="hidden" name="form-name" value="enquiry">', '')

if ($index -match 'data-netlify|netlify-honeypot|fetch\(\x27/\x27') {
    throw 'The Cloudflare staging form still contains Netlify transport markers.'
}
Set-Content -LiteralPath $indexPath -Value $index -Encoding UTF8

if (-not [string]::IsNullOrWhiteSpace($CanonicalBaseUrl)) {
    $canonicalUri = $null
    if (-not [Uri]::TryCreate($CanonicalBaseUrl.TrimEnd('/'), [UriKind]::Absolute, [ref]$canonicalUri) -or
        $canonicalUri.Scheme -ne 'https' -or $canonicalUri.AbsolutePath -ne '/') {
        throw 'CanonicalBaseUrl must be an HTTPS origin such as https://www.example.com'
    }
    $canonical = $CanonicalBaseUrl.TrimEnd('/')
    foreach ($file in $htmlPages + @('sitemap.xml', 'robots.txt')) {
        $path = Join-Path $outputPath $file
        $contents = Get-Content -LiteralPath $path -Raw -Encoding UTF8
        $contents = $contents.Replace('https://doublepillars.netlify.app', $canonical)
        Set-Content -LiteralPath $path -Value $contents -Encoding UTF8
    }
    Write-Output "Replaced the temporary Netlify SEO base in the staging copy with: $canonical"
} else {
    Write-Warning 'Canonical URLs remain unchanged at https://doublepillars.netlify.app. Choose and approve the production domain before deploying to production.'
}

if ($UseExtensionlessUrls) {
    foreach ($file in $htmlPages) {
        $path = Join-Path $outputPath $file
        $contents = Get-Content -LiteralPath $path -Raw -Encoding UTF8
        $contents = $contents.Replace('href="index.html#', 'href="/#')
        $contents = $contents.Replace('href="index.html"', 'href="/"')
        $contents = [regex]::Replace($contents, 'href="([a-z0-9-]+)\.html"', 'href="$1"', [System.Text.RegularExpressions.RegexOptions]::IgnoreCase)
        foreach ($pageName in $htmlPages) {
            $extensionlessName = [System.IO.Path]::GetFileNameWithoutExtension($pageName)
            $contents = $contents.Replace("'$pageName'", "'$extensionlessName'")
            $contents = $contents.Replace('"' + $pageName + '"', '"' + $extensionlessName + '"')
        }
        $absolutePagePattern = [regex]::Escape($canonical) + '/([a-z0-9-]+)\.html\b'
        $contents = [regex]::Replace($contents, $absolutePagePattern, { param($match) "$canonical/$($match.Groups[1].Value)" }, [System.Text.RegularExpressions.RegexOptions]::IgnoreCase)
        Set-Content -LiteralPath $path -Value $contents -Encoding UTF8
    }

    $sitemapPath = Join-Path $outputPath 'sitemap.xml'
    $sitemap = Get-Content -LiteralPath $sitemapPath -Raw -Encoding UTF8
    $sitemap = $sitemap.Replace('.html</loc>', '</loc>')
    Set-Content -LiteralPath $sitemapPath -Value $sitemap -Encoding UTF8

    @'
# Preserve the existing .html URLs as legacy entry points while Cloudflare serves
# one extensionless canonical URL for each page.
/index.html / 301
/accounting-management.html /accounting-management 301
/forensic-services.html /forensic-services 301
/tax-advisory-compliance.html /tax-advisory-compliance 301
/corporate-secretarial.html /corporate-secretarial 301
/corporate-advisory.html /corporate-advisory 301
/training.html /training 301
/payroll-services.html /payroll-services 301
/corporate-finance.html /corporate-finance 301
'@ | Set-Content -LiteralPath (Join-Path $outputPath '_redirects') -Encoding UTF8
    Write-Output 'Prepared extensionless canonical URLs plus legacy .html redirects in the staging copy.'
}

$headersPath = Join-Path $outputPath '_headers'
$headers = Get-Content -LiteralPath $headersPath -Raw -Encoding UTF8
if ($headers -notmatch 'X-Robots-Tag: noindex') {
    $headers += @"

# Keep Cloudflare preview and pages.dev hostnames out of search results.
https://:project.pages.dev/*
  X-Robots-Tag: noindex
https://:version.:project.pages.dev/*
  X-Robots-Tag: noindex
"@
    Set-Content -LiteralPath $headersPath -Value $headers -Encoding UTF8
}

$routesJson = @'
{
  "version": 1,
  "include": ["/api/contact"],
  "exclude": []
}
'@
$utf8NoBom = New-Object System.Text.UTF8Encoding($false)
[System.IO.File]::WriteAllText((Join-Path $outputPath '_routes.json'), $routesJson, $utf8NoBom)

$publishedFiles = Get-ChildItem -LiteralPath $outputPath -Recurse -Force -File |
    ForEach-Object { $_.FullName.Substring($outputPath.Length + 1) } |
    Sort-Object
Write-Output "Prepared Cloudflare Pages staging directory from existing dist: $outputPath"
Write-Output 'Existing dist was not modified.'
$publishedFiles | ForEach-Object { Write-Output " - $_" }
