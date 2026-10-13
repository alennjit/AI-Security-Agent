<#
.SYNOPSIS
    Read-only check that a Windows endpoint is correctly set up for AI Security Agent inspection.

.DESCRIPTION
    Changes nothing. Run on a pilot machine after the CA and PAC policies have applied. It checks:
      1. the inspection CA is trusted (by thumbprint),
      2. the PAC URL is configured,
      3. the PAC file downloads and looks valid,
      4. Windows routes a monitored AI host through the proxy, and a control host DIRECT,
      5. the TLS certificate the machine actually receives for the monitored host is issued by the
         inspection CA, and the one for the control host is NOT.
    Exit code 0 = all checks passed, 1 = at least one failed.

.EXAMPLE
    .\Test-AisaDeployment.ps1 -PacUrl http://proxy.corp.example/proxy.pac -ExpectedThumbprint FC897B9C474381D1C09196485486C73490CF91C5
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string]$PacUrl,
    [Parameter(Mandatory = $true)][ValidatePattern('^[0-9A-Fa-f]{40}$')][string]$ExpectedThumbprint,
    [string]$MonitoredHost = 'api.openai.com',
    [string]$ControlHost = 'example.com',
    [string]$CaIssuerText = 'AI Security Agent Inspection CA'
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Continue'

$results = New-Object System.Collections.Generic.List[object]
function Add-Result([string]$Check, [bool]$Pass, [string]$Detail) {
    $results.Add([pscustomobject]@{ Check = $Check; Result = $(if ($Pass) { 'PASS' } else { 'FAIL' }); Detail = $Detail })
}

# 1. CA trusted
$ca = Get-ChildItem -Path Cert:\LocalMachine\Root -ErrorAction SilentlyContinue | Where-Object { $_.Thumbprint -eq $ExpectedThumbprint.ToUpper() }
Add-Result '1. Inspection CA trusted' ([bool]$ca) $(if ($ca) { $ca.Subject } else { "thumbprint $($ExpectedThumbprint.ToUpper()) not in LocalMachine\Root" })

# 2. PAC URL configured (user preference/policy, or browser policy)
$configured = @()
foreach ($p in @(
        'HKCU:\Software\Microsoft\Windows\CurrentVersion\Internet Settings',
        'HKLM:\SOFTWARE\Policies\Google\Chrome',
        'HKLM:\SOFTWARE\Policies\Microsoft\Edge')) {
    $props = Get-ItemProperty -Path $p -ErrorAction SilentlyContinue
    if ($props) {
        foreach ($name in 'AutoConfigURL', 'ProxyPacUrl') {
            if ($props.PSObject.Properties.Name -contains $name -and $props.$name -eq $PacUrl) { $configured += "$p [$name]" }
        }
    }
}
Add-Result '2. PAC URL configured' ($configured.Count -gt 0) $(if ($configured.Count) { $configured -join '; ' } else { "no policy/preference sets $PacUrl" })

# 3. PAC downloads
try {
    $pac = Invoke-WebRequest -Uri $PacUrl -UseBasicParsing -TimeoutSec 15
    Add-Result '3. PAC file reachable' ($pac.Content -match 'FindProxyForURL') "HTTP $($pac.StatusCode), $($pac.Content.Length) bytes"
} catch {
    Add-Result '3. PAC file reachable' $false $_.Exception.Message
}

# 4. System routing decision
$systemProxy = [System.Net.WebRequest]::GetSystemWebProxy()
$monitoredVia = $systemProxy.GetProxy([uri]"https://$MonitoredHost/")
$controlVia = $systemProxy.GetProxy([uri]"https://$ControlHost/")
$monitoredProxied = $monitoredVia.Host -ne $MonitoredHost
$controlDirect = $controlVia.Host -eq $ControlHost
Add-Result "4a. $MonitoredHost routed via proxy" $monitoredProxied "-> $($monitoredVia.Authority)"
Add-Result "4b. $ControlHost goes DIRECT" $controlDirect "-> $($controlVia.Authority)"

# 5. Certificate actually received
# A compiled callback is used because .NET calls validation callbacks on another thread, where a
# PowerShell scriptblock has no runspace and silently fails to record anything.
if (-not ('AisaCertProbe' -as [type])) {
    Add-Type -TypeDefinition @'
using System.Net.Security;
using System.Security.Cryptography.X509Certificates;
public static class AisaCertProbe {
    public static string Issuer;
    private static bool Check(object sender, X509Certificate cert, X509Chain chain, SslPolicyErrors errors) {
        Issuer = cert.Issuer;
        return errors == SslPolicyErrors.None;
    }
    public static readonly RemoteCertificateValidationCallback Handler = Check;
}
'@
}
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12

function Get-IssuerSeen([string]$HostName, [string]$Path) {
    [AisaCertProbe]::Issuer = $null
    $old = [Net.ServicePointManager]::ServerCertificateValidationCallback
    [Net.ServicePointManager]::ServerCertificateValidationCallback = [AisaCertProbe]::Handler
    try { Invoke-WebRequest -Uri "https://$HostName$Path" -UseBasicParsing -TimeoutSec 20 | Out-Null } catch { }
    finally { [Net.ServicePointManager]::ServerCertificateValidationCallback = $old }
    return [AisaCertProbe]::Issuer
}
$monitoredIssuer = Get-IssuerSeen $MonitoredHost '/v1/models'
Add-Result "5a. $MonitoredHost cert issued by inspection CA" ($monitoredIssuer -and $monitoredIssuer -like "*$CaIssuerText*") "issuer: $monitoredIssuer"
$controlIssuer = Get-IssuerSeen $ControlHost '/'
Add-Result "5b. $ControlHost cert NOT from inspection CA" ($controlIssuer -and $controlIssuer -notlike "*$CaIssuerText*") "issuer: $controlIssuer"

$results | Format-Table -AutoSize -Wrap | Out-String | Write-Output
$failed = @($results | Where-Object { $_.Result -eq 'FAIL' }).Count
if ($failed -eq 0) { Write-Output 'ALL CHECKS PASSED'; exit 0 } else { Write-Output "$failed CHECK(S) FAILED"; exit 1 }
