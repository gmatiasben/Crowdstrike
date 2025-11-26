// Prerequisite: Configure 7d timeframe
// Gives Total GB/day - v1.0.0
// Matias Bendel by Crowdstrike
eventSize() 
| [sum("_eventSize", as=TotalGB)]
| TotalGB:=TotalGB/7
| TotalGB:=unit:convert("TotalGB", binary=true, from=B, to=G, keepUnit=true)
