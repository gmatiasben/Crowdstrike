// LDAPsearches hunting
#event_simpleName=ActiveDirectoryIncomingLdapSearchRequest
| groupBy([LdapSearchBaseObjectSample, ComputerName], function=([top([LdapSearchAttributes,LdapSearchFilterSample,SourceEndpointHostName,SourceAccount
