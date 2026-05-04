# YOU MUST REPLACE VALUES IN THIS SCRIPT BEFORE USING OR IT WILL NOT WORK

# Search for <REPLACE_WITH_URL> and replace that with the correct URL for your cloud
# US1: https://api.crowdstrike.com/aidr/aiguard
# US2: https://api.us-2.crowdstrike.com/aidr/aiguard

# Search for <REPLACE_WITH_REGISTRATION> and replace that with the registration identity value from the collector you are using

# Edge Extension ID
$extensionId = "folndgmoekgkipoolphnkclopeopkecc"

Write-Output "=== Installing Edge Extension for All Users ==="

# Step 1: Set HKLM policy for force install (applies to all users)
Write-Output "`n[Step 1] Setting machine-wide force install policy..."

$registryPath = "HKLM:\SOFTWARE\Policies\Microsoft\Edge\ExtensionInstallForcelist"

function Test-ExtensionInstalled {
    param($Path, $ExtId)
    
    if (!(Test-Path $Path)) { return $false }
    
    $existingEntries = Get-ItemProperty -Path $Path -ErrorAction SilentlyContinue
    if (!$existingEntries) { return $false }
    
    $found = $existingEntries.PSObject.Properties | 
        Where-Object { $_.Name -match '^\d+$' -and $_.Value -like "$ExtId;*" }
    
    return ($null -ne $found)
}

if (Test-ExtensionInstalled -Path $registryPath -ExtId $extensionId) {
    Write-Output "Extension already in force install list."
} else {
    if (!(Test-Path $registryPath)) {
        New-Item -Path $registryPath -Force | Out-Null
    }

    $existingEntries = Get-ItemProperty -Path $registryPath -ErrorAction SilentlyContinue
    $index = 1
    if ($existingEntries) {
        $existingNumbers = $existingEntries.PSObject.Properties | 
            Where-Object { $_.Name -match '^\d+$' } | 
            ForEach-Object { [int]$_.Name }
        if ($existingNumbers) {
            $index = ($existingNumbers | Measure-Object -Maximum).Maximum + 1
        }
    }

    New-ItemProperty -Path $registryPath -Name $index -Value "$extensionId;https://clients2.google.com/service/update2/crx" -PropertyType String -Force | Out-Null
    Write-Output "Extension added to force install list at index $index."
}

# Step 2: Set machine-wide extension policy configuration (non-user-specific settings)
Write-Output "`n[Step 2] Configuring extension policy (machine-wide)..."

$policyPath = "HKLM:\SOFTWARE\Policies\Microsoft\Edge\3rdparty\extensions\$extensionId\policy"

if (!(Test-Path $policyPath)) {
    New-Item -Path $policyPath -Force | Out-Null
    Write-Output "Created policy registry path."
}

# Set urlTemplate (same for all users)
New-ItemProperty -Path $policyPath -Name "urlTemplate" -Value "https://api.us-2.crowdstrike.com/aidr/aiguard" -PropertyType String -Force | Out-Null
Write-Output "Set urlTemplate."

# Set registrationIdentity (same for all users)
$registrationIdentity = "<REPLACE_WITH_REGISTRATION>"
New-ItemProperty -Path $policyPath -Name "registrationIdentity" -Value $registrationIdentity -PropertyType String -Force | Out-Null
Write-Output "Set registrationIdentity."

# Step 3: Configure per-user settings for all user profiles
Write-Output "`n[Step 3] Configuring per-user settings..."

# Get all user profiles on the system
$userProfiles = Get-ChildItem "Registry::HKEY_USERS" | Where-Object { $_.Name -match 'S-1-5-21-[\d\-]+$' }

$userCount = 0
foreach ($userProfile in $userProfiles) {
    $userSID = $userProfile.PSChildName
    
    try {
        # Try to get the username from the SID
        $objSID = New-Object System.Security.Principal.SecurityIdentifier($userSID)
        $objUser = $objSID.Translate([System.Security.Principal.NTAccount])
        $fullUsername = $objUser.Value
        
        # Extract short username (without domain)
        $shortUsername = $fullUsername
        if ($fullUsername -match '\\') {
            $shortUsername = $fullUsername.Split('\')[1]
        }
        
        # Set per-user policy path
        $userPolicyPath = "Registry::HKEY_USERS\$userSID\SOFTWARE\Policies\Microsoft\Edge\3rdparty\extensions\$extensionId\policy"
        
        if (!(Test-Path $userPolicyPath)) {
            New-Item -Path $userPolicyPath -Force | Out-Null
        }
        
        # Set userID to full username (including domain)
        New-ItemProperty -Path $userPolicyPath -Name "userID" -Value $fullUsername -PropertyType String -Force | Out-Null
        
        # Set userFullName to short username (without domain)
        New-ItemProperty -Path $userPolicyPath -Name "userFullName" -Value $shortUsername -PropertyType String -Force | Out-Null
        
        Write-Output "Configured for user: $fullUsername (short: $shortUsername)"
        $userCount++
        
    } catch {
        Write-Output "Warning: Could not process user SID $userSID - $_"
    }
}

Write-Output "Configured $userCount user profile(s)."

# Step 4: Set default user profile for future users
Write-Output "`n[Step 4] Configuring default user profile for future users..."

# Load default user hive temporarily
$defaultUserHive = "C:\Users\Default\NTUSER.DAT"
$tempHiveKey = "HKLM\TempDefaultUser"

if (Test-Path $defaultUserHive) {
    try {
        # Load the default user hive
        $result = reg load $tempHiveKey $defaultUserHive 2>&1
        
        if ($LASTEXITCODE -eq 0) {
            $defaultPolicyPath = "Registry::HKEY_LOCAL_MACHINE\TempDefaultUser\SOFTWARE\Policies\Microsoft\Edge\3rdparty\extensions\$extensionId\policy"
            
            if (!(Test-Path $defaultPolicyPath)) {
                New-Item -Path $defaultPolicyPath -Force | Out-Null
            }
            
            # Set placeholder values - these will be updated when the user logs in
            # The extension should handle reading the actual username at runtime
            New-ItemProperty -Path $defaultPolicyPath -Name "userID" -Value "%USERNAME%" -PropertyType String -Force | Out-Null
            New-ItemProperty -Path $defaultPolicyPath -Name "userFullName" -Value "%USERNAME%" -PropertyType String -Force | Out-Null
            
            Write-Output "Configured default user profile."
            
            # Unload the hive
            [gc]::Collect()
            Start-Sleep -Seconds 1
            reg unload $tempHiveKey | Out-Null
        } else {
            Write-Output "Note: Could not load default user hive. Future users will inherit machine policy."
        }
    } catch {
        Write-Output "Note: Could not configure default user profile - $_"
        # Try to unload if it was loaded
        reg unload $tempHiveKey 2>&1 | Out-Null
    }
} else {
    Write-Output "Note: Default user profile not found at expected location."
}

Write-Output "`n=== Configuration Complete ==="
Write-Output "Machine-wide policies have been set."
Write-Output "Per-user settings configured for $userCount existing user(s)."
Write-Output "Extension will install when users launch Edge."
Write-Output ""
Write-Output "For immediate effect on active sessions:"
Write-Output "1. Users must close ALL Edge windows"
Write-Output "2. Restart Edge"
Write-Output "3. Extension will auto-install on launch"
