# Get all shared folders on the local machine
$sharedFolders = Get-WmiObject -Class Win32_Share | Where-Object { $_.Type -eq 0 } # Type 0 indicates a disk drive share

Write-Host "Shared folders with 'Everyone' permissions:"
Write-Host "------------------------------------------"

foreach ($share in $sharedFolders) {
    $shareName = $share.Name
    $sharePath = $share.Path

    # Check Share Permissions for 'Everyone'
    $shareACL = Get-SmbShareAccess -Name $shareName -ErrorAction SilentlyContinue
    if ($shareACL | Where-Object { $_.AccountName -eq 'Everyone' -and $_.AccessRight -like '*Full*' }) {
        # Check NTFS Permissions for 'Everyone'
        try {
            $ntfsACL = Get-Acl -Path $sharePath
            $everyoneNTFSAccess = $ntfsACL.Access | Where-Object { $_.IdentityReference.Value -eq 'Everyone' }

            if ($everyoneNTFSAccess) {
                # You can refine this to check for specific NTFS permissions if needed
                # For example, if you only want 'FullControl':
                # if ($everyoneNTFSAccess | Where-Object { $_.FileSystemRights -match 'FullControl' }) {
                Write-Host "Share Name: $($shareName)"
                Write-Host "Path: $($sharePath)"
                Write-Host "  - Share Permissions: Everyone has Full Control"
                Write-Host "  - NTFS Permissions: Everyone has some level of access (check details if needed)"
                Write-Host ""
            }
        } catch {
            Write-Warning "Could not retrieve NTFS permissions for $($sharePath): $($_.Exception.Message)"
        }
    }
}
