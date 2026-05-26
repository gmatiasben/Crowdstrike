#event_simpleName=LFODownloadConfirmation FileName=/^C-00000085/ aid=?aid
| FileName=/^C-(?<Channel>\d+)\-\d+\-(?<Version>\d+)\.sys$/
| Channel:=round("Channel")
| Channel=?Channel
| Version:=round("Version")
| groupBy([aid, Channel], function=([selectFromMax(field="@timestamp", include=[ComputerName, ConfigStateHash, @timestamp, Version, FileName])]))
| rename([[@timestamp, Updated]]) | Updated:=formatTime(format="%F %T", field="Updated")
| table([aid, ComputerName, FileName, Channel, Version, ConfigStateHash, Updated], sortby=Version, order=des, limit=max)
