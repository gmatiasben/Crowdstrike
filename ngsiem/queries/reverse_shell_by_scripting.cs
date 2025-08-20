// Reverse Shell Hunting - Suspicious powershell script - v1.0.0
// Matias Bendel by Crowdstrike
#event_simpleName=/^(CommandHistory|NetworkConnectIP4)$/ event_platform=Win
| case{
    // Check to see if event is CommandHistory
    #event_simpleName=CommandHistory
    // This is keyword list; modify as desired
    | CommandHistory=/(ps1|System.Net.Sockets.TCPClient)/i
    // This puts the CommandHistory entries into an array
    | CommandHistorySplit:=splitString(by="¶", field=CommandHistory)
    // This combines the array values and separates them with a new-line
    | concatArray("CommandHistorySplit", separator="\n", as=CommandHistoryClean);
    // Map true remote IP address
    #event_simpleName=NetworkConnectIP4 | TrueRemoteIP:=RemoteIP 
    // Format ProcessStartTime to human-readable
    | ContextTimeStamp:=timestamp*1000 | ContextTimeStamp:=formatTime(format="%F %T.%L %Z", field="ContextTimeStamp");
}
// Unify UPID value
| falconPID:=TargetProcessId | falconPID:=ContextProcessId
// Use selfJoinFilter to pair PR2 and NET events
| selfJoinFilter(field=[aid, falconPID], where=[{#event_simpleName="NetworkConnectIP4"}, {#event_simpleName="CommandHistory"}])
// Aggregate to display details
| groupBy([aid, falconPID], function=([collect([ContextTimeStamp,ComputerName, UserName, ContextFileName, TrueRemoteIP, RemotePort, CommandHistoryClean])]), limit=max)
