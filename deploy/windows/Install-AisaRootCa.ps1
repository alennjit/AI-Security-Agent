<#
.SYNOPSIS
    Installs the AI Security Agent inspection CA into this machine's Trusted Root store.

.DESCRIPTION
    Safe-by-default installer for deployment through Datto RMM, a GPO startup script, or by hand.
    It REFUSES to install unless ALL of these hold:
      - the file's SHA-1 thumbprint equals -ExpectedThumbprint (printed by generate_ca.py),
      - the certificate carries a Name Constraints extension (a CA that can sign for ANY site is rejected),
      - the file contains no private key,
      - the certificate is a CA and has not expired.
    Use -WhatIf to see what would happen without changing anything. Requires an elevated session
    to actually install. Roll back with Remove-AisaRootCa.ps1.

.EXAMPLE
    .\Install-AisaRootCa.ps1 -CertPath .\ca-cert.cer -ExpectedThumbprint FC897B9C474381D1C09196485486C73490CF91C5 -WhatIf
#>
[CmdletBinding(SupportsShouldProcess = $true, ConfirmImpact = 'High')]
param(
    [Parameter(Mandatory = $true)][string]$CertPath,
    [Parameter(Mandatory = $true)][ValidatePattern('^[0-9A-Fa-f]{40}$')][string]$ExpectedThumbprint
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$NameConstraintsOid = '2.5.29.30'
$BasicConstraintsOid = '2.5.29.19'

if (-not (Test-Path -LiteralPath $CertPath -PathType Leaf)) { throw "Certificate file not found: $CertPath" }

try {
    $cert = New-Object System.Security.Cryptography.X509Certificates.X509Certificate2 -ArgumentList (Resolve-Path -LiteralPath $CertPath).Path
} catch {
    throw "Refusing to install: '$CertPath' could not be read as a public certificate. Deploy ca-cert.cer only - never the mitmproxy-ca.pem file, which contains the private key."
}

if ($cert.Thumbprint -ne $ExpectedThumbprint.ToUpper()) {
    throw "Thumbprint mismatch. File is $($cert.Thumbprint) but $($ExpectedThumbprint.ToUpper()) was expected. Refusing to install."
}
if ($cert.HasPrivateKey) {
    throw 'Refusing to install: the file contains a private key. Deploy only the public certificate (ca-cert.cer).'
}
if (-not ($cert.Extensions | Where-Object { $_.Oid.Value -eq $NameConstraintsOid })) {
    throw 'Refusing to install: the certificate has no Name Constraints extension. Only name-constrained inspection CAs may be trusted.'
}
$basic = $cert.Extensions | Where-Object { $_.Oid.Value -eq $BasicConstraintsOid }
if (-not $basic -or -not $basic.CertificateAuthority) { throw 'Refusing to install: the certificate is not a CA certificate.' }
if ($cert.NotAfter -lt (Get-Date)) { throw "Refusing to install: the certificate expired on $($cert.NotAfter)." }

$existing = Get-ChildItem -Path Cert:\LocalMachine\Root | Where-Object { $_.Thumbprint -eq $cert.Thumbprint }
if ($existing) {
    Write-Output "Already installed: $($cert.Subject) [$($cert.Thumbprint)]. Nothing to do."
    return
}

$target = "Cert:\LocalMachine\Root"
if ($PSCmdlet.ShouldProcess($target, "Trust $($cert.Subject) [$($cert.Thumbprint)], valid until $($cert.NotAfter.ToString('yyyy-MM-dd'))")) {
    $identity = [Security.Principal.WindowsIdentity]::GetCurrent()
    $isAdmin = (New-Object Security.Principal.WindowsPrincipal $identity).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
    if (-not $isAdmin) { throw 'Installing into the machine store requires an elevated (administrator) session.' }

    Import-Certificate -FilePath $cert.PSPath.Replace('Microsoft.PowerShell.Core\FileSystem::', '') -CertStoreLocation $target -ErrorAction Stop | Out-Null
    $verify = Get-ChildItem -Path Cert:\LocalMachine\Root | Where-Object { $_.Thumbprint -eq $cert.Thumbprint }
    if (-not $verify) { throw 'Install appeared to succeed but the certificate is not in the store.' }
    Write-Output "Installed and verified: $($cert.Subject) [$($cert.Thumbprint)]"
}
