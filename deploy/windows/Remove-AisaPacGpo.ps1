<#
.SYNOPSIS
    Rolls back New-AisaPacGpo.ps1: unlinks and deletes the PAC GPO.

.DESCRIPTION
    Removes all links to the GPO, then deletes it. Clients drop the proxy settings at their next policy
    refresh. Note: the HKCU AutoConfigURL value is a Group Policy PREFERENCE, so on some machines it can
    persist after the GPO is gone; the -Cleanup helper line in docs/DEPLOYMENT.md shows how to clear it.
    Supports -WhatIf.
#>
[CmdletBinding(SupportsShouldProcess = $true, ConfirmImpact = 'High')]
param(
    [string]$GpoName = 'AI Security Agent - Proxy PAC',
    # Distinguished names of the OUs the GPO was linked to, e.g. "OU=AI-Pilot,DC=corp,DC=example"
    [string[]]$TargetOu = @()
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

if (-not (Get-Module -ListAvailable -Name GroupPolicy)) { throw 'The GroupPolicy module (RSAT) is not available on this machine.' }
Import-Module GroupPolicy

$gpo = Get-GPO -Name $GpoName -ErrorAction SilentlyContinue
if (-not $gpo) {
    Write-Output "No GPO named '$GpoName'. Nothing to do."
    return
}

[xml]$report = Get-GPOReport -Name $GpoName -ReportType Xml
$links = @($report.GPO.LinksTo | Where-Object { $_ })

Write-Output "GPO '$GpoName' is currently linked to $($links.Count) location(s):"
$links | ForEach-Object { Write-Output "  - $($_.SOMPath)" }
if ($links.Count -gt $TargetOu.Count) {
    Write-Warning 'More links exist than -TargetOu values were given. Unlink the rest in GPMC, or any left behind show as links to a missing GPO (harmless, but untidy).'
}

if ($PSCmdlet.ShouldProcess($GpoName, "Unlink from $($TargetOu.Count) OU(s) and delete")) {
    foreach ($ou in $TargetOu) {
        Remove-GPLink -Name $GpoName -Target $ou -ErrorAction Stop | Out-Null
        Write-Output "Unlinked: $ou"
    }
    Remove-GPO -Name $GpoName -ErrorAction Stop
    Write-Output "Deleted GPO '$GpoName'."
}
