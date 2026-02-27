// FileVantage Linux - SUDO user identification - v1.0.0
// Matias Bendel by Crowdstrike
#event_simpleName=/^(FileIntegrityMonitorRuleMatched|ProcessRollup2)$/ event_platform=Lin
| case{
    #event_simpleName=FileIntegrityMonitorRuleMatched
    | ParentImageFileName=/sudo/i
    | sudo := "sudo "
    | concat([sudo, CommandLine], as=CommandLineFIM);
    #event_simpleName="ProcessRollup2" 
    | CommandLine=/sudo/i
    | CommandLinePR2:=CommandLine;
}
| CommandLineID:=CommandLinePR2 | CommandLineID:=CommandLineFIM
| selfJoinFilter(field=[aid,CommandLineID], where=[{#event_simpleName="ProcessRollup2"}, {#event_simpleName="FileIntegrityMonitorRuleMatched"}])
| groupBy([aid,CommandLineID,ProcessStartTime], function=([collect([ComputerName, RUID, UserName])]), limit=max)
| RUID != 0
| ProcessStartTime:=ProcessStartTime*1000 | ProcessStartTime:=formatTime(format="%F %T.%L %Z", field="ProcessStartTime")
