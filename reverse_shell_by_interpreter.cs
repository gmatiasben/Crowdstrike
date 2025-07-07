// Reverse Shell Hunting - Suspicious Interpreters or Apps - v1.0.0
// Matias Bendel by Crowdstrike
#event_simpleName=/^(NetworkConnectIP4|ProcessRollup2)$/ event_platform=Win
| case{
    // Check to see if event is ProcessRollup2. If yes, create mini process tree
    #event_simpleName="ProcessRollup2" 
    // Pre-Filter witk lookup file
    | match(file="rsh_filename.csv", field=FileName, ignoreCase=true, strict=true)
    // Check to see if event is ProcessRollup2. If yes, create mini process tree
    | ExecutionChain:=format(format="%s\n\t└ %s (%s)", field=[ParentBaseFileName, FileName, RawProcessId]);
    // Do nothing
    #event_simpleName=NetworkConnectIP4;
}
// Unify UPID value
| falconPID:=TargetProcessId | falconPID:=ContextProcessId
// Use selfJoinFilter to pair PR2 and NET events
| selfJoinFilter(field=[aid, falconPID], where=[{#event_simpleName="ProcessRollup2"}, {#event_simpleName="NetworkConnectIP4"}])
// Aggregate to display details
| groupBy([aid, falconPID], function=([collect([ProcessStartTime, ComputerName, UserName, ExecutionChain, ParentBaseFileName, FileName, RawProcessId, RemoteIP, RemotePort])]))
// Format ProcessStartTime to human-readable
| ProcessStartTime:=ProcessStartTime*1000 | ProcessStartTime:=formatTime(format="%F %T.%L %Z", field="ProcessStartTime")
// Remove duplicated columns
| select(aid, falconPID, ProcessStartTime, ComputerName, UserName, ExecutionChain, RemoteIP, RemotePort)