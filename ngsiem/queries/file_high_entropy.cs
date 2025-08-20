// Entropy Threshold Exceeded - v1.0.0
// Matias Bendel by Crowdstrike
"#event_simpleName" = /^(ProcessRollup2|FileWrittenWithEntropyHigh)$/ event_platform=Win
| case{
    // Check to see if event is ProcessRollup2. If yes, create mini process tree
    #event_simpleName="FileWrittenWithEntropyHigh" 
    // Pre-Filter - Individual Entropy
    | ShannonEntropy > 990;
    // Do nothing
    #event_simpleName=ProcessRollup2;
}
// Unify UPID value
| falconPID:=TargetProcessId | falconPID:=ContextProcessId
// Use selfJoinFilter to pair PR2 and Entropy events
| selfJoinFilter(field=[aid, falconPID], where=[{#event_simpleName="ProcessRollup2"}, {#event_simpleName="FileWrittenWithEntropyHigh"}])
// Aggregate to display details
| groupBy([aid,falconPID], function=([collect([ProcessStartTime, ComputerName, UserName, ImageFileName, FileName, ShannonEntropy]), sum(ShannonEntropy, as=EntropySum)]), limit=max)
// Format ProcessStartTime to human-readable
| ProcessStartTime:=ProcessStartTime*1000 | ProcessStartTime:=formatTime(format="%F %T.%L %Z", field="ProcessStartTime")
// Apply detection to Microsoft and Adobe files
| FileName = *.pdf or FileName = *.xls* or FileName = *.ppt* or FileName = *.doc*
// Entropy Threshold
| EntropySum > 2500
