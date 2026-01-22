// Privilege Escalation Hunting CQL Query - v1.0.0
// Matias Bendel by Crowdstrike
#event_simpleName=/^(AssociateIndicator|CommandHistory)$/
| case{
    // Check to see if event is AssociateIndicator
    #event_simpleName=AssociateIndicator
    // Filter by Tactic
    | Tactic=/(Privilege Escalation)/i;
    #event_simpleName=CommandHistory;
}
// Use selfJoinFilter to pair AIn & CH events
| selfJoinFilter(field=[aid, TargetProcessId], where=[{#event_simpleName="CommandHistory"}, {#event_simpleName="AssociateIndicator"}])
// Aggregate to display details
| groupBy([aid, TargetProcessId], function=([collect([LogonTime, ComputerName, event_platform, UserName, Tactic, Technique, CommandHistory])]), limit=max)
// Format LogonTime to human-readable
| LogonTime:=LogonTime*1000 | LogonTime:=formatTime(format="%F %T.%L %Z", field="LogonTime")
