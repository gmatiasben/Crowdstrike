eventSize() 
| [sum("_eventSize", as=TotalBytes), groupby([#Vendor], function=([count(), sum("_eventSize", as=SizeBytes)]))]
| SizeGB:=unit:convert("SizeBytes", binary=true, from=B, to=G, keepUnit=true)
| TotalGB:=unit:convert("TotalBytes", binary=true, from=B, to=G, keepUnit=true)
| sort(SizeBytes, order=desc, limit=10)
| pct := (SizeBytes/TotalBytes)*100 | format(format="%,.3f%%", field=[pct], as=pct)
| drop(_count,SizeBytes,TotalBytes)
