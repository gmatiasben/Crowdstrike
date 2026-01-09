// Assicate Indicators Hunting - Retrieve further information from processes - v1.0.0
// Matias Bendel by Crowdstrike
#event_simpleName=/^(AssociateIndicator|ProcessRollup2)$/ event_platform=Win
| case{
    // Do nothing
    #event_simpleName=AssociateIndicator;
    // Check to see if event is ProcessRollup2. If yes, create mini process tree
    #event_simpleName="ProcessRollup2" | ExecutionChain:=format(format="%s\n\t└ %s (%s)", field=[ParentBaseFileName, FileName, RawProcessId]);
}
// Use selfJoinFilter to pair AI and PR2 events
| selfJoinFilter(field=[aid, TargetProcessId], where=[{#event_simpleName="AssociateIndicator"}, {#event_simpleName="ProcessRollup2"}])
// Aggregate to display details
| groupBy([aid, TargetProcessId], function=([collect([ProcessStartTime, ComputerName, UserName, ExecutionChain, Command, Tactic, Technique, DetectDescription, DetectName, DetectScenario, DetectSeverity])]), limit=max)
// Format ProcessStartTime to human-readable
| ProcessStartTime:=ProcessStartTime*1000 | ProcessStartTime:=formatTime(format="%F %T.%L %Z", field="ProcessStartTime")
