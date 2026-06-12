#repo="detections" ExternalApiType=/Remote/
| array:regex("Commands[]", regex="cat|get|put|memdump|xmemdump|run|put-and-run")
| concatArray("Commands", separator="; ", as=Commands)
| Commands=*
| groupBy([UserName, AgentIdString], function=([collect([timestamp,Commands])]))
| AgentIdString=~match(file="aid_master_main.csv", column=[aid], strict=false)
