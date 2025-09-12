function Invoke-Ldap {

    param(
       [string]
       [ValidateNotNullOrEmpty()]
       $DC,
   
       [ValidateSet('Base', 'OneLevel', 'Subtree')]
       [String]
       $SearchScope = 'Subtree',
   
       [ValidateNotNullOrEmpty()]
       [String]
       $LDAPFilter,
   
       [ValidateNotNullOrEmpty()]
       [String[]]
       $Properties,
   
       [ValidateRange(1, 10000)]
       [Int]
       $ResultPageSize = 0,
   
       [ValidateRange(1, 10000)]
       [Int]
       $ServerTimeLimit
    )
   
   
       $SearchString = "LDAP://$($DC)"
       $Searcher = New-Object System.DirectoryServices.DirectorySearcher([ADSI]$SearchString)
   
   
       $Searcher.SizeLimit = $ResultPageSize
       $Searcher.SearchScope = $SearchScope
       $Searcher.CacheResults = $False
       $Searcher.ServerTimeLimit = $ServerTimeLimit
       $Searcher.filter = $LDAPFilter
       $PropertiesToLoad = $Properties| ForEach-Object { $_.Split(',') }
       $Searcher.PropertiesToLoad.AddRange(($PropertiesToLoad))
   
       return $Searcher.FindAll()
   }
   
   
   
   function Invoke-LDAPCase
   {
       param(
   
           [ValidateNotNullOrEmpty()]
           [string]
           $LDAPToken,
   
           [ValidateNotNullOrEmpty()]
           [string]
           $dc
       )
       $res = "None"
   
       switch ($LDAPToken)
       {
   
           "DCA0F320-DB30-36BA-ABAF-8C16E2207393" {$res = Invoke-Ldap -DC $dc -SearchScope Base -LDAPFilter "(distinguishedname=ldap_test)" -Properties "msds-membertransitive,objectsid"}
   
           "48BFA131-977C-33A7-B95C-EA77DC145188" {$res = Invoke-Ldap -DC $dc -SearchScope Base -LDAPFilter "(distinguishedname=ldap_test)" -Properties "admincount,useraccountcontrol,msds-replattributemetadata"}
   
           "E8E6DC4E-2960-389A-B1EC-71D653C952BE" {$res = Invoke-Ldap -DC $dc -SearchScope Subtree -LDAPFilter "(&(objectClass=user)(objectCategory=person)(WhenCreated>=20230601080000.000-0700))" -Properties "sAMAccountName,whencreated,accountExpires,useraccountcontrol,HomeMDB,msExchHideFromAddressLists,msRTCSIP-UserEnabled,proxyaddresses,objectclass,subschemaSubentry"}
   
           "970F72D7-74B4-3EFD-964B-611563D3ACDE" {$res = Invoke-Ldap -DC $dc -SearchScope Subtree -LDAPFilter "(&(admincount=1)(!(samaccountname=test))(!(memberof:1.2.840.113556.1.4.1941:=CN=Domain Admins,CN=Users,DC=det19,DC=idpro))(!(distinguishedname=test))(!(memberof:1.2.840.113556.1.4.1941:=CN=Domain Admins,CN=Users,DC=det19,DC=idpro))(!(distinguishedname=test))(!(memberof:1.2.840.113556.1.4.1941:=CN=Domain Admins,CN=Users,DC=det19,DC=idpro))(!(distinguishedname=test))(!(memberof:1.2.840.113556.1.4.1941:=CN=Domain Admins,CN=Users,DC=det19,DC=idpro))(!(distinguishedname=test))(!(memberof:1.2.840.113556.1.4.1941:=CN=Domain Admins,CN=Users,DC=det19,DC=idpro))(!(distinguishedname=test))(!(memberof:1.2.840.113556.1.4.1941:=CN=Domain Admins,CN=Users,DC=det19,DC=idpro))(!(distinguishedname=test))(!(memberof:1.2.840.113556.1.4.1941:=CN=Domain Admins,CN=Users,DC=det19,DC=idpro))(!(distinguishedname=test))(!(memberof:1.2.840.113556.1.4.1941:=CN=Domain Admins,CN=Users,DC=det19,DC=idpro))(!(distinguishedname=test))(!(memberof:1.2.840.113556.1.4.1941:=CN=Domain Admins,CN=Users,DC=det19,DC=idpro))(!(distinguishedname=test))(!(memberof:1.2.840.113556.1.4.1941:=CN=Domain Admins,CN=Users,DC=det19,DC=idpro))(!(distinguishedname=test))(!(memberof:1.2.840.113556.1.4.1941:=CN=Domain Admins,CN=Users,DC=det19,DC=idpro))(!(distinguishedname=test))(!(memberof:1.2.840.113556.1.4.1941:=CN=Domain Admins,CN=Users,DC=det19,DC=idpro))(!(distinguishedname=test))(!(memberof:1.2.840.113556.1.4.1941:=CN=Domain Admins,CN=Users,DC=det19,DC=idpro))(!(distinguishedname=test)))" -Properties "samaccountname,objectclass,msds-replattributemetadata"}
   
           "FF58C36D-45D5-3FB7-9EAF-1AFF61E58D11" {$res = Invoke-Ldap -DC $dc -SearchScope Subtree -LDAPFilter "(&(objectcategory=test)(!(trustattributes:1.2.840.113556.1.4.803:=18))(!(trustattributes:1.2.840.113556.1.4.803:=1))(trustdirection:1.2.840.113556.1.4.803:=1)(!(trustattributes:1.2.840.113556.1.4.803:=1)))" -Properties "trustattributes,trustpartner"}
   
           "E338F735-2D7C-3910-9BAD-F281AF2307A0" {$res = Invoke-Ldap -DC $dc -SearchScope Subtree -LDAPFilter "(ms-mcs-admpwdexpirationtime=*)" -Properties "ntsecuritydescriptor"}
   
           "0F2E79B8-9917-313D-9E9B-9F3C1E18BC42" {$res = Invoke-Ldap -DC $dc -SearchScope Base -LDAPFilter "(objectCategory=*)" -Properties "dnsHostName,distinguishedName,objectClass"}
   
           "7FF28C97-5EAA-370C-9550-FEA5C1E067C7" {$res = Invoke-Ldap -DC $dc -SearchScope Subtree -LDAPFilter "(&(!(admincount=1))(samaccounttype=test)(!(useraccountcontrol:1.2.840.113556.1.4.803:=2))(!(pwdlastset=20080812000000.0Z))(pwdlastset<=20080812000000.0Z))" -Properties "samaccountname,msds-replattributemetadata,pwdlastset"}
   
           “B27AED11-D983-37D6-81D2-4EBCA740ABB8” {$res = Invoke-Ldap -DC $dc -SearchScope Base -LDAPFilter “(objectClass=*)” -Properties "objectClass,distinguishedName,instanceType,whenCreated,whenChanged,subRefs,uSNCreated,dSASignature,repsFrom,uSNChanged,nTSecurityDescriptor,name,objectGUID,replUpToDateVector,creationTime,forceLogoff,lockoutDuration,lockOutObservationWindow,lockoutThreshold,maxPwdAge,minPwdAge,minPwdLength,modifiedCountAtLastProm,nextRid,pwdProperties,pwdHistoryLength,objectSid,uASCompat,modifiedCount,auditingPolicy,nTMixedDomain,rIDManagerReference,fSMORoleOwner,systemFlags,wellKnownObjects,objectCategory,isCriticalSystemObject,gPLink,gPOptions,dSCorePropagationData,otherWellKnownObjects,masteredBy,ms-DS-MachineAccountQuota,msDS-Behavior-Version,msDS-PerUserTrustQuota,msDS-AllUsersTrustQuota,msDS-PerUserTrustTombstonesQuota,msDs-masteredBy,msDS-IsFullReplicaFor,msDS-IsDomainFor,msDS-IsPartialReplicaFor,msDS-NcType,msDS-ExpirePasswordsOnSmartCardOnlyAccounts,dc,canonicalName” -ResultPageSize 10000 }
   
           "42357CBF-45B3-3B8F-B18F-0D0F0684AD62" {$res = Invoke-Ldap -DC $dc -SearchScope Subtree -LDAPFilter "(samaccounttype=ldap_test)" -Properties "objectsid"}
   
       }
       return $res
   }

$global:testList = @(
"dca0f320-db30-36ba-abaf-8c16e2207393",
"48bfa131-977c-33a7-b95c-ea77dc145188",
"e8e6dc4e-2960-389a-b1ec-71d653c952be",
"970f72d7-74b4-3efd-964b-611563d3acde",
"ff58c36d-45d5-3fb7-9eaf-1aff61e58d11",
"e338f735-2d7c-3910-9bad-f281af2307a0",
"0f2e79b8-9917-313d-9e9b-9f3c1e18bc42",
"7ff28c97-5eaa-370c-9550-fea5c1e067c7",
"b27aed11-d983-37d6-81d2-4ebca740abb8",
"42357cbf-45b3-3b8f-b18f-0d0f0684ad62"
)

$dcHost = ($env:LOGONSERVER).Replace('\\','')
$domain = (gwmi WIN32_ComputerSystem).Domain
$global:dcFQDN = $dcHost + "." + $domain

function run {
if (!$dcFQDN) {
    throw "Unable to determine domain controller FQDN. Please modify the script manually at line 111 and retry"
}
write-host "Running queries against Domain Controller: $dcfqdn..." -ForegroundColor Green
foreach ($i in $testList) {
    $error.clear()
    try {
    Invoke-LDAPCase -LDAPToken $i -dc $dcFQDN
    write-host "Successfully Run Test $i..." -ForegroundColor Green
    }
    catch {
        $lasterror = $error[0].Exception | Select-Object Message
        write-host "Failed to run Test $i...error is: $lasterror" -ForegroundColor red 
    }
}
}

