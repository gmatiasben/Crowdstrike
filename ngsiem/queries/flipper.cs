// Flipper detection - v1.0.0
// Matias Bendel by Crowdstrike
#event_simpleName=/^(DcUsbDeviceConnected|ProcessRollup2)$/ event_platform=Win
| case{
    #event_simpleName=DcUsbDeviceConnected
    // Filtering for HIDClass
    | DevicePropertyClassName = HIDClass
    | DeviceTime := timestamp;
    #event_simpleName="ProcessRollup2"
    | ProcessTime := timestamp
    // Filtering for cerrtain processes
    | in(field="FileName", values=[cmd.exe, powershell.exe, notepad.exe], ignoreCase=true) 
    | ExecutionChain:=format(format="%s\n\t└ %s (%s)", field=[ParentBaseFileName, FileName, RawProcessId]);
}
| selfJoinFilter(field=[aid], where=[{#event_simpleName="ProcessRollup2"}, {#event_simpleName="DcUsbDeviceConnected"}])
| groupBy([aid], function=([collect([ComputerName, DeviceTimeStamp, ProcessTime, DeviceTime, UserName, ExecutionChain, DeviceManufacturer, DeviceProduct, DeviceInstanceId])]), limit=max)
// Adjustment to GMT-4
| DeviceTimeStamp:=(DeviceTimeStamp-(3600*4))*1000 | DeviceTimeStamp:=formatTime(format="%F %T", field="DeviceTimeStamp")
| DiffTime := ProcessTime - DeviceTime
// USB connection should happened before the execution of the process
| DiffTime > 0
// The execution of the process shouldn't be more than 12 second from the connection of the USB
| DiffTime < 12000
