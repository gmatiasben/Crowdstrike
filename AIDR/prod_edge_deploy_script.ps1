$RegistrationIdentity = "<REPLACE_WITH_REGISTRATION>"
$ErrorActionPreference = "Stop"

$extensionId = "folndgmoekgkipoolphnkclopeopkecc"
$updateUrl   = "https://clients2.google.com/service/update2/crx"

# ── Force-install path (correct) ─────────────────────────────────────────────
$forceInstallPath = "HKLM:\Software\Policies\Microsoft\Edge\ExtensionInstallForcelist"

# ── Managed storage policy path ───────────────────────────────────────────────
$policyPath = "HKLM:\Software\Policies\Microsoft\Edge\3rdparty\extensions\$extensionId\policy"

try {

    # ── Step 1: Write force-install entry to correct path ─────────────────────
    if (!(Test-Path $forceInstallPath)) {
        New-Item -Path $forceInstallPath -Force | Out-Null
    }

    # Check if already present to avoid duplicates
    $existingValues = Get-Item -Path $forceInstallPath | Select-Object -ExpandProperty Property
    $extensionEntry = "$extensionId;$updateUrl"
    $alreadyPresent = $false

    foreach ($valueName in $existingValues) {
        $val = (Get-ItemProperty -Path $forceInstallPath -Name $valueName).$valueName
        if ($val -eq $extensionEntry) {
            Write-Output "Extension already present in force-install list at index: $valueName"
            $alreadyPresent = $true
            break
        }
    }

    if (-not $alreadyPresent) {
        $numericValues = $existingValues | Where-Object { $_ -match '^\d+$' } | ForEach-Object { [int]$_ }
        $nextIndex     = if ($numericValues) { ($numericValues | Measure-Object -Maximum).Maximum + 1 } else { 1 }
        New-ItemProperty -Path $forceInstallPath -Name "$nextIndex" -Value $extensionEntry -PropertyType String -Force | Out-Null
        Write-Output "Extension added to force-install list at index: $nextIndex"
    }

    # ── Step 2: Write managed storage policy ──────────────────────────────────
    if (!(Test-Path $policyPath)) {
        New-Item -Path $policyPath -Force | Out-Null
    }

    Set-ItemProperty -Path $policyPath -Name "registrationIdentity" `
        -Value $RegistrationIdentity `
        -Type String -Force

    Set-ItemProperty -Path $policyPath -Name "urlTemplate" `
        -Value "https://api.us-2.crowdstrike.com/aidr/aiguard" `
        -Type String -Force

    New-ItemProperty -Path $policyPath -Name "userId" `
        -Value "%USERNAME%" -PropertyType ExpandString -Force | Out-Null

    New-ItemProperty -Path $policyPath -Name "userFullName" `
        -Value "%COMPUTERNAME%\%USERNAME%" -PropertyType ExpandString -Force | Out-Null

    # ── Step 3: Verify ────────────────────────────────────────────────────────
    $config = Get-ItemProperty -Path $policyPath
    $forceInstallConfig = Get-ItemProperty -Path $forceInstallPath

    Write-Output "========================================================"
    Write-Output "Configuration applied successfully"
    Write-Output "  Force-install path : $forceInstallPath"
    Write-Output "  Policy path        : $policyPath"
    Write-Output "  registrationIdentity : Set"
    Write-Output "  urlTemplate          : $($config.urlTemplate)"
    Write-Output "  userId               : $($config.userId)"
    Write-Output "  userFullName         : $($config.userFullName)"
    Write-Output "========================================================"

    Exit 0

} catch {
    Write-Error "Failed: $($_.Exception.Message)"
    Exit 1
}
