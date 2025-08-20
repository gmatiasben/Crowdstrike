// Reverse Shell Hunting - Suspicious file download - v1.0.0
// Matias Bendel by Crowdstrike
#event_simpleName=/^(CommandHistory|ProcessRollup2)$/ event_platform=Win
| case{
    // Check to see if event is CommandHistory
    #event_simpleName=CommandHistory
    // This is keyword list; modify as desired
    | CommandHistory=/(curl|wget|Invoke-WebRequest)/i
    // This puts the CommandHistory entries into an array
    | CommandHistorySplit:=splitString(by="¶", field=CommandHistory)
    // Search array for certain commands
    | objectArray:eval(array="CommandHistorySplit[]", var=x, asArray="out[]", function={ x=/(curl|wget|Invoke-WebRequest)/i | out:=x }) | Command:=out[0];
    // Check to see if event is ProcessRollup2. If yes, create mini process tree
    #event_simpleName="ProcessRollup2" | ExecutionChain:=format(format="%s\n\t└ %s (%s)", field=[ParentBaseFileName, FileName, RawProcessId]);
}
// Use selfJoinFilter to pair PR2 and CH events
| selfJoinFilter(field=[aid, TargetProcessId], where=[{#event_simpleName="ProcessRollup2"}, {#event_simpleName="CommandHistory"}])
// Aggregate to display details
| groupBy([aid, TargetProcessId], function=([collect([ProcessStartTime, ComputerName, UserName, ExecutionChain, Command])]), limit=max)
// Format ProcessStartTime to human-readable
| ProcessStartTime:=ProcessStartTime*1000 | ProcessStartTime:=formatTime(format="%F %T.%L %Z", field="ProcessStartTime")
