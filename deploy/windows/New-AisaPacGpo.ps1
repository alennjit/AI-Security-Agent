<#
.SYNOPSIS
    Creates the Group Policy Object that points browsers and Windows at the AI Security Agent PAC file.

.DESCRIPTION
    Run from a domain-joined machine with the GroupPolicy module (RSAT) and rights to create GPOs.
    SAFE DEFAULTS:
      - The GPO is created UNLINKED. Nothing applies to any machine until you link it.
      - Linking needs -Link plus an explicit -TargetOu, and a domain-root target is refused.
        Link to a small pilot OU first, then widen.
      - Supports -WhatIf.
    It sets:
      - User preference:  HKCU\Software\Microsoft\Windows\CurrentVersion\Internet Settings\AutoConfigURL
        (Windows system proxy, used by Edge/Chrome and most apps)
      - Policy:           Chrome and Edge ProxyMode=pac_script and ProxyPacUrl
    It does NOT distribute the inspection CA. Trust the CA with a SEPARATE GPO scoped to the same OU
    (Computer Configuration > Policies > Windows Settings > Security Settings > Public Key Policies >
    Trusted Root Certification Authorities) or with Install-AisaRootCa.ps1. Do not use `certutil -dspublish`:
    that publishes trust domain-wide. Roll back with Remove-AisaPacGpo.ps1.

.EXAMPLE
    .\New-AisaPacGpo.ps1 -PacUrl http://proxy.corp.example/proxy.pac -WhatIf
    .\New-AisaPacGpo.ps1 -PacUrl http://proxy.corp.example/proxy.pac -Link -TargetOu "OU=AI-Pilot,DC=corp,DC=example"
#>
[CmdletBinding(SupportsShouldProcess = $true, ConfirmImpact = 'High')]
param(
    [Parameter(Mandatory = $true)][ValidatePattern('^https?://[^\s"]+$')][string]$PacUrl,
    [string]$GpoName = 'AI Security Agent - Proxy PAC',
    [switch]$Link,
    [string]$TargetOu
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

if ($Link -and -not $TargetOu) { throw '-Link requires an explicit -TargetOu (use a small pilot OU first).' }
if ($TargetOu -and $TargetOu -match '^\s*DC=') { throw "Refusing to link at the domain root ($TargetOu). Link to an OU." }
if (-not (Get-Module -ListAvailable -Name GroupPolicy)) { throw 'The GroupPolicy module (RSAT) is not available on this machine.' }
Import-Module GroupPolicy

if (Get-GPO -Name $GpoName -ErrorAction SilentlyContinue) {
    throw "A GPO named '$GpoName' already exists. Remove it with Remove-AisaPacGpo.ps1 or choose another -GpoName."
}

if ($PSCmdlet.ShouldProcess($GpoName, "Create UNLINKED GPO pointing at $PacUrl")) {
    $gpo = New-GPO -Name $GpoName -Comment "AI Security Agent: routes AI-service traffic to the inspection proxy via PAC. Created $(Get-Date -Format s)."

    Set-GPPrefRegistryValue -Name $GpoName -Context User -Action Replace `
        -Key 'HKCU\Software\Microsoft\Windows\CurrentVersion\Internet Settings' `
        -ValueName 'AutoConfigURL' -Type String -Value $PacUrl | Out-Null

    foreach ($browserKey in 'HKLM\SOFTWARE\Policies\Google\Chrome', 'HKLM\SOFTWARE\Policies\Microsoft\Edge') {
        Set-GPRegistryValue -Name $GpoName -Key $browserKey -ValueName 'ProxyMode' -Type String -Value 'pac_script' | Out-Null
        Set-GPRegistryValue -Name $GpoName -Key $browserKey -ValueName 'ProxyPacUrl' -Type String -Value $PacUrl | Out-Null
    }
    Write-Output "Created GPO '$GpoName' (id $($gpo.Id)). It is NOT linked; nothing is applied yet."

    if ($Link) {
        if ($PSCmdlet.ShouldProcess($TargetOu, "Link GPO '$GpoName'")) {
            New-GPLink -Name $GpoName -Target $TargetOu -LinkEnabled Yes | Out-Null
            Write-Output "Linked to $TargetOu."
        }
    } else {
        Write-Output 'Review the GPO, then re-run with -Link -TargetOu "<pilot OU>" or link it in GPMC.'
    }
}
