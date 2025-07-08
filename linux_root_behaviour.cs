// Reverse Shell Hunting - Suspicious file download - v1.0.0
// Matias Bendel by Crowdstrike
#event_simpleName=ProcessRollup2 event_platform=Lin
// Filter root User
| UserName = root
// Aggregate to display details
| groupBy([aid, ComputerName], function=([top([ProcessStartTime,CommandLine], limit=10)]))
// Format ProcessStartTime to human-readable
| ProcessStartTime:=ProcessStartTime*1000 | ProcessStartTime:=formatTime(format="%F %T.%L %Z", field="ProcessStartTime")
