#event_simpleName=ActiveDirectoryServiceAccessRequest
| service.name="FILE_SHARE"
| groupBy([ComputerName], function=([top([network.protocol,source.user.name,TargetServiceAccessIdentifier])]), limit=max)
