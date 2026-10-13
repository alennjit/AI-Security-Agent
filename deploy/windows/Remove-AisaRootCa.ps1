<#
.SYNOPSIS
    Rolls back Install-AisaRootCa.ps1: removes the inspection CA from the Trusted Root store.

.DESCRIPTION
    Removes exactly one certificate, identified by thumbprint, from Cert:\LocalMachine\Root.
    Supports -WhatIf. Requires an elevated session to actually remove.

.EXAMPLE
    .\Remove-AisaRootCa.ps1 -Thumbprint FC897B9C474381D1C09196485486C73490CF91C5 -WhatIf
#>
[CmdletBinding(SupportsShouldProcess = $true, ConfirmImpact = 'High')]
param(
    [Parameter(Mandatory = $true)][ValidatePattern('^[0-9A-Fa-f]{40}$')][string]$Thumbprint
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$thumb = $Thumbprint.ToUpper()
$found = Get-ChildItem -Path Cert:\LocalMachine\Root | Where-Object { $_.Thumbprint -eq $thumb }
if (-not $found) {
    Write-Output "Not installed: $thumb. Nothing to do."
    return
}

if ($PSCmdlet.ShouldProcess("Cert:\LocalMachine\Root\$thumb", "Remove trust for $($found.Subject)")) {
    $identity = [Security.Principal.WindowsIdentity]::GetCurrent()
    $isAdmin = (New-Object Security.Principal.WindowsPrincipal $identity).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
    if (-not $isAdmin) { throw 'Removing from the machine store requires an elevated (administrator) session.' }

    Remove-Item -Path "Cert:\LocalMachine\Root\$thumb" -ErrorAction Stop
    if (Get-ChildItem -Path Cert:\LocalMachine\Root | Where-Object { $_.Thumbprint -eq $thumb }) {
        throw 'Removal did not take effect.'
    }
    Write-Output "Removed: $thumb"
}
