// Count number of events for the last week
eventSize() 
| [sum("_eventSize", as=TotalGB)]
| TotalGB:=TotalGB/7
| TotalGB:=unit:convert("TotalGB", binary=true, from=B, to=G, keepUnit=true)
