// LDAPsearches hunting
#event_simpleName=ActiveDirectoryIncomingLdapSearchRequest
| groupBy([ComputerName], function=([top([LdapSearchBaseObjectSample,LdapSearchAttributes,LdapSearchFilterSample,SourceEndpointHostName,SourceAccount])]), limit=max)
//| _count > 2
