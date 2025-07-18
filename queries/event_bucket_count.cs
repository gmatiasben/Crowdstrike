// Count number of events for the top 10 event buckets
eventSize() 
| [sum("_eventSize", as=total), groupby([#event_simpleName], function=([count(), sum("_eventSize", as=SizeBytes)]))]
| SizeGB:=unit:convert("SizeBytes", binary=true, from=B, to=G, keepUnit=true)
| sort(SizeBytes, order=desc, limit=10)
| pct := (SizeBytes/total)*100 | format(format="%,.3f%%", field=[pct], as=pct)
