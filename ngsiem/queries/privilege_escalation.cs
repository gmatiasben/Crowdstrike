// Privilege Escalation Hunting CQL Query - v1.0.0
// Matias Bendel by Crowdstrike
#event_simpleName=/^(AssociateIndicator|ProcessRollup2)$/
| case{
    // Check to see if event is AssociateIndicator
    #event_simpleName=AssociateIndicator
    // Filter by Tactic
    | Tactic=/(Privilege Escalation)/i;
    // Check to see if event is ProcessRollup2. If yes, create mini process tree
    #event_simpleName="ProcessRollup2" | ExecutionChain:=format(format="%s\n\t└ %s (%s)", field=[ParentBaseFileName, FileName, RawProcessId]);
}
// Use selfJoinFilter to pair PR2 and AIn events
| selfJoinFilter(field=[aid, TargetProcessId], where=[{#event_simpleName="ProcessRollup2"}, {#event_simpleName="AssociateIndicator"}])
// Aggregate to display details
| groupBy([aid, TargetProcessId], function=([collect([ProcessStartTime, ComputerName, event_platform, UserName, Tactic, Technique, ExecutionChain, MD5HashData, CommandLine])]), limit=max)
// Format ProcessStartTime to human-readable
| ProcessStartTime:=ProcessStartTime*1000 | ProcessStartTime:=formatTime(format="%F %T.%L %Z", field="ProcessStartTime")
