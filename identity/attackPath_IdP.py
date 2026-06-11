#!/usr/bin/env python3

################################################################################################
####### API REQUIREMENTS ###########
# Identity Protection Entities: Read
# Identity Protection GraphQL: Write
####### API REQUIREMENTS ###########

####### General Information ########
# This Python3 script utilizes the Falcon API to pull out all attack path information contained within IDP.
# Below you will find the script, some output example files, and some basic guidance around running the tool.
# The script is capable of outputting data to two types of files: CSV and LOG. The LOG file is just time stamped text output.
# There is also a verbose mode to print all data to the screen. 
####### General Information ########

####### Run Examples ########
# Run the tool (outputs to XLSX with multiple views into attack paths)
# python3 attackPath_IDP.py -c 1
# 
####### Run Examples ########

####### CrowdStrike Scripts & Code License Agreement ########
# (c) Copyright CrowdStrike 2024-25
# By accessing or using this script, sample code, application programming interface, tools, and/or associated
# documentation (if any) (collectively, "Tools"), You (i) represent and warrant that You are entering into this
# Agreement on behalf of a company, organization or another legal entity ("Entity") that is currently a
# customer or partner of CrowdStrike, Inc. ("CrowdStrike"), and (ii) have the authority to bind such Entity
# and such Entity agrees to be bound by this Agreement.
#
# CrowdStrike grants Entity a non-exclusive, non-transferable, non-sublicensable, royalty free and limited
# license to access and use the Tools solely for Entity's internal business purposes and in accordance with
# its obligations under any agreement(s) it may have with CrowdStrike. Entity acknowledges and agrees that
# CrowdStrike and its licensors retain all right, title and interest in and to the Tools, and all intellectual
# property rights embodied therein, and that Entity has no right, title or interest therein except for the
# express licenses granted hereunder and that Entity will treat such Tools as CrowdStrike's confidential
# information.
#
# THE TOOLS ARE PROVIDED "AS-IS" WITHOUT WARRANTY OF ANY KIND, WHETHER EXPRESS, IMPLIED OR
# STATUTORY OR OTHERWISE. CROWDSTRIKE SPECIFICALLY DISCLAIMS ALL SUPPORT OBLIGATIONS AND
# ALL WARRANTIES, INCLUDING WITHOUT LIMITATION, ALL IMPLIED WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR PARTICULAR PURPOSE, TITLE, AND NON-INFRINGEMENT. IN NO EVENT SHALL CROWDSTRIKE
# BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION)
# HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR
# TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THE TOOLS,
# EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
################################################################################################


import json, requests, os, re
from random import uniform
from time import sleep
from datetime import datetime, timedelta, timezone
from getpass import getpass
from optparse import OptionParser
from openpyxl import Workbook
from pathlib import Path


def getToken(falconURL, apiClient, apiSecret, last_token=None, last_token_time=None):
    """ 
    Dedicated function to get/renew the auth/bearer token
    Returns a tuple to include the time the token was requested
    """

    # Let's configure the authorization request with the necessary data
    authurl = falconURL+'/oauth2/token'
    auth_headers = {
        "accept": "application/json",
        "Content-Type": "application/x-www-form-urlencoded"
    }
    authdata={
        "client_id":apiClient,
        "client_secret":apiSecret
    }

    if last_token_time and last_token:
        delta = datetime.now(timezone.utc) - last_token_time

        # Check if our token is older than 25 min
        if (delta.total_seconds() / 60) <= 25:
            return last_token, last_token_time
        else:
            print("[+] Refreshing Auth Token")

    # Get & decode bearer token
    r = requests.post(authurl,headers=auth_headers,params=authdata)
    token_time = datetime.now(timezone.utc)
    auth_string = r.content.decode('utf8')
    json_auth = json.loads(auth_string)
    bearer = json_auth['access_token']

    # Setup the header for future requests
    idp_header = {
        "Authorization": "Bearer " + bearer,
        "Content-Type": "application/json",
        "Accept": "application/json"
        }

    return idp_header, token_time

def queryData(falconURL, runQuery, client, secret, verbose=True, resumeCursor=None):
    """Efficient GraphQL paginator with rate-limit, token awareness, and progress tracking."""

    def safe_post(query, variables=None, token=None):
        """Post request wrapper with retry and jitter."""
        retries = 0
        while retries < 5:
            try:
                response = requests.post(
                    idp_url,
                    headers=token,
                    json={'query': query, 'variables': variables}
                )
                result = json.loads(response.content.decode('utf-8'))

                # Error check
                if 'errors' in result:
                    raise Exception(result['errors'])

                return result
            except Exception as e:
                retries += 1
                sleep_time = uniform(2, 5) * (2 ** retries)
                if verbose:
                    print(f"[!] Retry #{retries} after error: {e}")
                sleep(sleep_time)
        raise Exception("Max retries exceeded")

    # Prep
    idp_url = falconURL + "/identity-protection/combined/graphql/v1"
    token, token_time = getToken(falconURL, client, secret)
    token_expires = token_time + timedelta(minutes=27)

    # Get total count
    countQuery = """query {
      countEntities(riskFactorTypes: [HAS_ATTACK_PATH], archived: false)
    }"""
    countResult = safe_post(countQuery, token=token)
    totalEntityCount = countResult.get("data", {}).get("countEntities", 0)

    if verbose:
        print(f"[+] Starting GraphQL paginated query... Expecting ~{totalEntityCount} entities")

    cursor = resumeCursor
    nodes = []
    totalRetrieved = 0

    while True:
        # Token refresh if needed
        if datetime.now(timezone.utc) > token_expires:
            if verbose:
                print("[*] Refreshing token")
            token, token_time = getToken(falconURL, client, secret)
            token_expires = token_time + timedelta(minutes=28)

        variables = {"after": cursor} if cursor else {}
        result = safe_post(runQuery, variables, token)

        # Parse result
        entities = result['data']['entities']
        current_nodes = entities['nodes']
        nodes.extend(current_nodes)
        totalRetrieved += len(current_nodes)
        pageInfo = entities['pageInfo']
        extensions = result.get('extensions', {})

        # Log with progress
        consumed = extensions.get("consumedPoints", 0)
        remaining = extensions.get("remainingPoints", 0)
        runtime = extensions.get("runTime", 0)
        
        if verbose:
            print(f"[→] {datetime.now(timezone.utc).strftime('%Y_%m_%d %H-%M-%S')} - Got {totalRetrieved}/{totalEntityCount} nodes | Consumed: {consumed} | Remaining: {remaining} | Runtime: {runtime}ms")

        # Smart throttling
        if remaining < 100000:
            sleep_time = 10 if remaining > 50000 else 30
            jitter = uniform(1, 3)
            if verbose:
                print(f"[Zzz] {datetime.now(timezone.utc).strftime('%Y_%m_%d %H-%M-%S')} - Low quota: Sleeping {sleep_time + jitter:.1f}s to avoid lockout")
            sleep(sleep_time + jitter)

        # Pagination logic
        if pageInfo['hasNextPage']:
            cursor = pageInfo['endCursor']
        else:
            break

    return nodes

def parseNodesForExport(nodeData):
    """Takes in GraphQL node data and exports to CSV"""

    # Set initial attack variable to be used later for iteration
    attack = 1

    # Not needed but setting up variables for CSV writing
    csv_start_entity = ""
    csv_start_entity_type = ""
    csv_start_entity_enabled = True
    csv_dest_entity = ""
    csv_dest_entity_type = ""
    csv_dest_entity_enabled = True
    csv_attackpath_steps = 0
    csv_attackpath_relations = []
    csv_attackpath_relations_clean = ""
    csv_path_details = ""
    csv_complete_row = []
    summary_complete_row = []

    # If we're exporting all steps then need additional variables
    steps_complete_row = []

    for n in nodeData:
        riskFactors = n['riskFactors']
        attack += 1
        
        csv_start_entity = n['secondaryDisplayName']
        csv_start_entity_enabled = n['accounts'][0]['enabled']
        
        for m in riskFactors:
            if(m['type'] == 'HAS_ATTACK_PATH'):
                attackPath = m['attackPath']
                count = 1
                
                # Let's start iterating through all attack path steps
                for e in attackPath:
                    # Let's get all the relations information to add to the CSV
                    if(e['relation'] not in csv_attackpath_relations):
                        csv_attackpath_relations.append(e['relation'].strip())
                        csv_attackpath_relations.sort()
                    
                    if(count == 1): # Need to grab some data on the starting entity on the first pass only
                        csv_start_entity_type = e['entity']['type']
                        csv_path_details = ""
                    
                    # First Links in Attack Path Chain
                    if(e['relation'] == 'DUPLICATE_PASSWORD'):
                        csv_path_details += "{}.{} ({} | {}:{}) and {} ({} | {}:{}) have the same password".format(count,e['entity']['primaryDisplayName'],e['entity']['secondaryDisplayName'],e['entity']['type'],e['entity']['riskScoreSeverity'],e['nextEntity']['primaryDisplayName'],e['nextEntity']['secondaryDisplayName'],e['nextEntity']['type'],e['nextEntity']['riskScoreSeverity'])
                        csv_path_details += "\n"
                        count += 1

                    if(e['relation'] == 'DUPLICATED_LOCAL_ADMIN'):
                        csv_path_details += "{}.{} ({}|{}:{}) has a local administrator with the same password as a local administrator on {} ({}:{})".format(count,e['entity']['primaryDisplayName'],e['entity']['secondaryDisplayName'],e['entity']['type'],e['entity']['riskScoreSeverity'],e['nextEntity']['primaryDisplayName'],e['nextEntity']['type'],e['nextEntity']['riskScoreSeverity'])
                        csv_path_details += "\n"
                        count += 1

                    if(e['relation'] == 'LOCAL_ADMIN'):
                        csv_path_details += "{}.{} ({}|{}:{}) is a local administrator on {} ({}:{})".format(count,e['entity']['primaryDisplayName'],e['entity']['secondaryDisplayName'],e['entity']['type'],e['entity']['riskScoreSeverity'],e['nextEntity']['primaryDisplayName'],e['nextEntity']['type'],e['nextEntity']['riskScoreSeverity'])
                        csv_path_details += "\n"
                        count += 1
                    
                    if(e['relation'] == 'LOGGED_ON_TO_EP'):
                        csv_path_details += "{}.{} ({}:{}) was recently accessed by {} ({}:{})".format(count,e['entity']['primaryDisplayName'],e['entity']['type'],e['entity']['riskScoreSeverity'],e['nextEntity']['primaryDisplayName'],e['nextEntity']['type'],e['nextEntity']['riskScoreSeverity'])
                        csv_path_details += "\n"
                        count += 1

                    # Middle Links, in addition to the first link list, can be one of:
                    
                    if(e['relation'] == 'IN_GROUP'):
                        csv_path_details += "{}.{} ({}|{}:{}) is a (direct/indirect) member of {} ({}:{})".format(count,e['entity']['primaryDisplayName'],e['entity']['secondaryDisplayName'],e['entity']['type'],e['entity']['riskScoreSeverity'],e['nextEntity']['primaryDisplayName'],e['nextEntity']['type'],e['nextEntity']['riskScoreSeverity'])
                        csv_path_details += "\n"
                        count += 1
                    
                    if(e['relation'] == 'ALLOWED_TO_ADD_TO_GROUP'):
                        csv_path_details += "{}.{} ({}|{}:{}) permitted to add itself to the group {} ({}:{})".format(count,e['entity']['primaryDisplayName'],e['entity']['secondaryDisplayName'],e['entity']['type'],e['entity']['riskScoreSeverity'],e['nextEntity']['primaryDisplayName'],e['nextEntity']['type'],e['nextEntity']['riskScoreSeverity'])
                        csv_path_details += "\n"
                        count += 1

                    if(e['relation'] == 'ALLOWED_TO_MODIFY_PERMISSIONS'):
                        csv_path_details += "{}.{} ({}|{}:{}) is permitted to gain control over {} ({}:{}) by modifying its ACL".format(count,e['entity']['primaryDisplayName'],e['entity']['secondaryDisplayName'],e['entity']['type'],e['entity']['riskScoreSeverity'],e['nextEntity']['primaryDisplayName'],e['nextEntity']['type'],e['nextEntity']['riskScoreSeverity'])
                        csv_path_details += "\n"
                        count += 1
                    
                    if(e['relation'] == 'PASSWORD_RESETTER'):
                        csv_path_details += "{}.{} ({}|{}:{}) permitted to reset {}'s password ({}:{})".format(count,e['entity']['primaryDisplayName'],e['entity']['secondaryDisplayName'],e['entity']['type'],e['entity']['riskScoreSeverity'],e['nextEntity']['primaryDisplayName'],e['nextEntity']['type'],e['nextEntity']['riskScoreSeverity'])
                        csv_path_details += "\n"
                        count += 1
                    
                    if(e['relation'] == 'ALLOWED_TO_ENROLL_CA_TEMPLATE'):
                        csv_path_details += "{}.{} ({}|{}:{}) is allowed to enroll for a certificate on behalf of any user using a certificate template on {} ({}:{})".format(count,e['entity']['primaryDisplayName'],e['entity']['secondaryDisplayName'],e['entity']['type'],e['entity']['riskScoreSeverity'],e['nextEntity']['primaryDisplayName'],e['nextEntity']['type'],e['nextEntity']['riskScoreSeverity'])
                        csv_path_details += "\n"
                        count += 1
                    
                    if(e['relation'] == 'ALLOWED_TO_WRITE_DACL_CA_TEMPLATE'):
                        csv_path_details += "{}.{} ({}|{}:{}) is allowed to gain control over certificate template on {} ({}:{}) using WriteDACL permissions".format(count,e['entity']['primaryDisplayName'],e['entity']['secondaryDisplayName'],e['entity']['type'],e['entity']['riskScoreSeverity'],e['nextEntity']['primaryDisplayName'],e['nextEntity']['type'],e['nextEntity']['riskScoreSeverity'])
                        csv_path_details += "\n"
                        count += 1

                    if(e['relation'] == 'ALLOWED_TO_WRITE_OWNER_CA_TEMPLATE'):
                        csv_path_details += "{}.{} ({}|{}:{}) is allowed to gain control over certificate template on {} ({}:{}) using WriteOwner permissions".format(count,e['entity']['primaryDisplayName'],e['entity']['secondaryDisplayName'],e['entity']['type'],e['entity']['riskScoreSeverity'],e['nextEntity']['primaryDisplayName'],e['nextEntity']['type'],e['nextEntity']['riskScoreSeverity'])
                        csv_path_details += "\n"
                        count += 1

                    if(e['relation'] == 'ALLOWED_TO_WRITE_PROPERTY_CA_TEMPLATE'):
                        csv_path_details += "{}.{} ({}|{}:{}) is allowed to gain control over certificate template on {} ({}:{}) using WriteProperty permissions".format(count,e['entity']['primaryDisplayName'],e['entity']['secondaryDisplayName'],e['entity']['type'],e['entity']['riskScoreSeverity'],e['nextEntity']['primaryDisplayName'],e['nextEntity']['type'],e['nextEntity']['riskScoreSeverity'])
                        csv_path_details += "\n"
                        count += 1

                    if(e['relation'] == 'ALLOWED_TO_WRITE_KEY_CREDENTIAL'):
                        csv_path_details += "{}.{} ({}|{}:{}) is allowed to control credentials of {} ({}:{}) by modifying msDS-KeyCredentialLink attribute".format(count,e['entity']['primaryDisplayName'],e['entity']['secondaryDisplayName'],e['entity']['type'],e['entity']['riskScoreSeverity'],e['nextEntity']['primaryDisplayName'],e['nextEntity']['type'],e['nextEntity']['riskScoreSeverity'])
                        csv_path_details += "\n"
                        count += 1

                    if(e['relation'] == 'OWNER_ADMIN'):
                        csv_path_details += "{}.{} ({}|{}:{}) is listed as the owner of {} ({}:{}) and can gain control of this account by modifying security descriptors.".format(count,e['entity']['primaryDisplayName'],e['entity']['secondaryDisplayName'],e['entity']['type'],e['entity']['riskScoreSeverity'],e['nextEntity']['primaryDisplayName'],e['nextEntity']['type'],e['nextEntity']['riskScoreSeverity'])
                        csv_path_details += "\n"
                        count += 1
                    
                    # Last links will always be a privileged account (with exclusion of business and extensive local admin privileges), one of:
                    
                    if(e['relation'] == 'ADMIN_REPLICATOR'):
                        csv_path_details += "{}.{} ({}|{}:{}) permitted to replicate domain information, including hashes.".format(count,e['entity']['primaryDisplayName'],e['entity']['secondaryDisplayName'],e['entity']['type'],e['entity']['riskScoreSeverity'])
                        csv_path_details += "\n"
                        count += 1
                    
                    if(e['relation'] == 'ADMIN'):
                        csv_path_details += "{}.{} ({}|{}:{}) is privileged.".format(count,e['entity']['primaryDisplayName'],e['entity']['secondaryDisplayName'],e['entity']['type'],e['entity']['riskScoreSeverity'])
                        csv_path_details += "\n"
                        count += 1

                    if(e['relation'] == 'ADMIN_SID_TAKEOVER'):
                        csv_path_details += "{}.{} ({}|{}:{}) receives privileges granted by sidHistory Active Directory attribute.".format(count,e['entity']['primaryDisplayName'],e['entity']['secondaryDisplayName'],e['entity']['type'],e['entity']['riskScoreSeverity'])
                        csv_path_details += "\n"
                        count += 1
                    
                    if(e['relation'] == 'ADMIN_UNCONSTRAINED_SVC_DELEGATION'):
                        csv_path_details += "{}.{} ({}|{}:{}) permitted to use authentication material to access any resource in the domain on behalf of other non-protected accounts, including privileged users.".format(count,e['entity']['primaryDisplayName'],e['entity']['secondaryDisplayName'],e['entity']['type'],e['entity']['riskScoreSeverity'])
                        csv_path_details += "\n"
                        count += 1
                    
                    if(e['relation'] == 'ADMIN_CONSTRAINED_SVC_DELEGATION'):
                        csv_path_details += "{}.{} ({}|{}:{}) permitted to access privileged resources on behalf of other non-protected accounts, including privileged users.".format(count,e['entity']['primaryDisplayName'],e['entity']['secondaryDisplayName'],e['entity']['type'],e['entity']['riskScoreSeverity'])
                        csv_path_details += "\n"
                        count += 1

                    if(e['relation'] == 'APPLICATION_CONTROLLER'):
                        csv_path_details += "{}.{} ({}|{}:{}) is an application controller for {} ({})".format(count,e['entity']['primaryDisplayName'],e['entity']['secondaryDisplayName'],e['entity']['type'],e['entity']['riskScoreSeverity'],e['nextEntity']['primaryDisplayName'],e['nextEntity']['type'])
                        csv_path_details += "\n"
                        count += 1

                    if(e['relation'] == 'APPLICATION_OWNER'):
                        csv_path_details += "{}.{} ({}|{}:{}) is the owner of the application {} ({})".format(count,e['entity']['primaryDisplayName'],e['entity']['secondaryDisplayName'],e['entity']['type'],e['entity']['riskScoreSeverity'],e['nextEntity']['primaryDisplayName'],e['nextEntity']['type'])
                        csv_path_details += "\n"
                        count += 1
                    
                    ############################################
                    # AP Step Exporting
                    ############################################
                    ap_start_ent = n['secondaryDisplayName'] + " (" + n['type'] + ")"
                    ap_dest_ent = attackPath[-1]['entity']['secondaryDisplayName'] + " (" + attackPath[-1]['entity']['type'] + ")"
                    # Header format: ['AP Start (Type)', 'AP Destination (Type)', 'Step Starting Entity', 'Step Starting Entity Type', 'Step Relation', 'Step Destination Entity', 'Step Destination Entity Type']

                    if e['relation'] in ['ADMIN_REPLICATOR', 'ADMIN', 'ADMIN_UNCONSTRAINED_SVC_DELEGATION', 'ADMIN_CONSTRAINED_SVC_DELEGATION', 'ADMIN_SID_TAKEOVER']:
                        # Certain relations don't have e['nextEntity']
                        steps_complete_row.append([ap_start_ent, ap_dest_ent, e['entity']['secondaryDisplayName'], e['entity']['type'], e['relation'] , "N/A", "N/A"])
                    else:
                        steps_complete_row.append([ap_start_ent, ap_dest_ent, e['entity']['secondaryDisplayName'], e['entity']['type'], e['relation'], e['nextEntity']['secondaryDisplayName'], e['nextEntity']['type']])


                # Now need to remove the last newline otherwise the CSV output appears blank
                csv_path_details = csv_path_details[:len(csv_path_details)-1]

                # Clean up the relations so that we can add to the CSV
                for val in csv_attackpath_relations:
                    csv_attackpath_relations_clean += val
                    if((val != csv_attackpath_relations[-1]) and len(csv_attackpath_relations) > 1):
                        csv_attackpath_relations_clean += ", "
                
                # Need to grab the count for the CSV after internal for loop, also write details of this path to CSV
                csv_attackpath_steps = count - 1
                csv_dest_entity = attackPath[-1]['entity']['secondaryDisplayName']
                csv_dest_entity_type = attackPath[-1]['entity']['type']
                csv_dest_entity_enabled = attackPath[-1]['entity']['accounts'][0]['enabled']

                #########################################################
                # If we're deduping then we need to check for duplicates
                # Current logic: 
                #       row[3] = Destination entity
                #       row[7] = attack path relations
                #
                # If both destination entity and attack path RELATIONS are the same, then consider them similar enough for summary
                #########################################################

                # Need a tracker for if a match was found
                row_match = False

                # Assuming we have data in the list to check against, otherwise go to else
                if len(summary_complete_row) > 0:
                    # Check for duplicate in the dest name first, then the relations
                    for row in summary_complete_row:
                        if row[3] == csv_dest_entity:
                            if row[7] == csv_attackpath_relations_clean:
                                row[9] += 1                         # increment the counter
                                row[10] += csv_start_entity + " "    # Add the similar entity
                                row_match = True                    # Set match tracker to True
                                break                               # Leave the for loop
                    if not row_match:
                        summary_complete_row.append([csv_start_entity, csv_start_entity_type, csv_start_entity_enabled, csv_dest_entity, csv_dest_entity_type, csv_dest_entity_enabled, csv_attackpath_steps, csv_attackpath_relations_clean, csv_path_details, 0, ""])
                
                else: # Case no 1 when list is empty
                    summary_complete_row.append([csv_start_entity, csv_start_entity_type, csv_start_entity_enabled, csv_dest_entity, csv_dest_entity_type, csv_dest_entity_enabled, csv_attackpath_steps, csv_attackpath_relations_clean, csv_path_details, 0, ""])
                
                # For the full AP data
                # Gather all the attack path info for the entity and write to list
                csv_complete_row.append([csv_start_entity, csv_start_entity_type, csv_start_entity_enabled, csv_dest_entity, csv_dest_entity_type, csv_dest_entity_enabled, csv_attackpath_steps, csv_attackpath_relations_clean, csv_path_details])
                
                # Reset these values for the next run
                csv_attackpath_relations = []
                csv_attackpath_relations_clean = ""
    

    return csv_complete_row, summary_complete_row, steps_complete_row

def exportXLSX(write_data_dict, header_dict, f_name, output_dir):
    """
    Efficient export of tabular data to XLSX using write-only mode.
    Each key in write_data_dict is the sheet name, with a list of row lists.
    header_dict must provide the column headers per tab.
    """

    def clean_excel_string(val):
        return re.sub(r"[\x00-\x08\x0B\x0C\x0E-\x1F]", "", val)

    # Resolve path
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
    fullpath = os.path.join(output_dir, f_name)

    wb = Workbook(write_only=True)

    for sheet_name, rows in write_data_dict.items():
        print(f"[-] Writing sheet: {sheet_name}")
        ws = wb.create_sheet(title=sheet_name)

        # Write headers
        headers = header_dict.get(sheet_name, [])
        ws.append([clean_excel_string(h[:32767]) if isinstance(h, str) else h for h in headers])

        # Write data rows
        for data_row in rows:
            sanitized_row = []
            for val in data_row:
                if isinstance(val, str):
                    val = clean_excel_string(val[:32767])
                sanitized_row.append(val)
            ws.append(sanitized_row)

    wb.save(fullpath)
    print(f"[✓] XLSX export complete: {fullpath}")
    return True

def findAPGoodies(all_steps_data):
    """ Within the final tab of the export, this function will note some interesting attack paths in the final column, otherwise will append a blank item to each column
        Input list of lists looks like this:
        [
            [0] AP Starting Entity
            [1] AP Destination Entity
            [2] Step Starting Entity
            [3] Step Starting Entity Type
            [4] AP Relation
            [5] Step Destination Entity --> This will be 'N/A' if it's the final step of the AP
            [6] Step Destination Entity Type --> This will be 'N/A' if it's the final step of the AP

        ]
    """
    
    notated_steps_data = []

    for step in all_steps_data:
        notes = "" # Used to append notes
        
        # Reset machine account password
        if step[4] == "PASSWORD_RESETTER" and step[6] == "ENDPOINT":
            notes = "Reset machine account password"
        
        # Domain Users Local Admin
        if step[4] == "LOCAL_ADMIN" and "Domain Users" in step[2]:
            notes = "Domain Users group in local admin"

        # Shadow Credentials
        if step[4] == 'ALLOWED_TO_WRITE_KEY_CREDENTIAL':
            notes = "Shadow Credentials - Modification of msds-KeyCredentialLink attribute"
        
        # ADCS
        if "CA_TEMPLATE" in step[4]:
            notes = "AD Certificate Services Abuse"

        # SidHistory Attack
        if step[4] == 'ADMIN_SID_TAKEOVER':
            notes = "SIDHistory attack potential"

        # Note lets update this data with any notes
        if notes:
            temp_list = step
            temp_list.append(notes)
            notated_steps_data.append(temp_list)

    return notated_steps_data

def main():
    parser = OptionParser(usage="Usage: %prog [options]", version="%prog 5.0")
    parser.add_option("-c", "--cloud", dest = "cloud_opt", help="Select which Falcon cloud to use - '1': (US-1) '2': (US-2) '3': (EU-1) '4': (US-GOV-1)")
    parser.add_option("-C", "--client_id", dest="client_id", help="Optional: Define the API Client ID as a parameter")
    parser.add_option("-S", "--secret", dest="secret", help="Optional: Define the API Secret as a parameter")
    parser.add_option("-p", "--pattern", dest = "dom_pattern", help="Specifcy domains to gather data from. Comma separated if multiple. E.g: 'DOMAIN1.COM,DOMAIN2.COM'")
    parser.add_option("-o", "--output_dir", dest = "output_dir", help="Optional: Provide the ABSOLUTE (NOT relative) output directory path to export to files to if not the CWD")
    (options, args) = parser.parse_args()


    ############################################################
    # Options checking
    ############################################################
    # Need to handle for different clouds
    cloud_dict = {
        '1': 'https://api.crowdstrike.com',
        '2': 'https://api.us-2.crowdstrike.com',
        '3': 'https://api.eu-1.crowdstrike.com',
        '4': 'https://api.laggar.gcw.crowdstrike.com'
    }
    if options.cloud_opt:
        # Error check input
        if str(options.cloud_opt) not in ['1', '2', '3', '4']:
            print("Please enter only '1', '2', '3', or '4' when using the '-c' or '--cloud' parameters.")
            exit(0)
        baseurl = cloud_dict[str(options.cloud_opt)]
    else:
        cloud_select = input("Which Falcon cloud to use? \n1: (US-1) \n2: (US-2) \n3: (EU-1) \n4: (US-GOV-1) \nEnter Choice (1-4): ")
        # Error check input
        if str(cloud_select) not in ['1', '2', '3', '4']:
            print("Please enter only '1', '2', '3', or '4'. ")
            exit(0)
        baseurl = cloud_dict[str(cloud_select)]        
    if not options.dom_pattern:
        dom_pattern="*"
    else:
        dom_pattern=options.dom_pattern

    # Let's validate the output directory if used
    output_dir = ""
    if options.output_dir:
        if Path(options.output_dir).is_dir():
            output_dir = Path(options.output_dir)
        else:
            print("[!] Output directory submitted does not exist. Please use a valid (existing) directory.")
            exit(0)

    ############################################################
    # Get API Key
    ############################################################
    
    # Get API Key
    if not options.client_id:
        client=getpass('Client Key: ')
    else:
        client=options.client_id
    
    if not options.secret:
        secret=getpass('Secret Key: ')
    else:
        secret=options.secret

    # Get initial token
    initial_token, initial_token_time = getToken(baseurl, client, secret)

    ############################################################
    # Query for entities | Parse Data | Export to XLSX
    ############################################################
    
    # Query used to get entities with attack path risk factor

    if not options.dom_pattern:
        query = """
        query ($after: Cursor)
        {
            entities(
            archived: false
            first: 1000
            riskFactorTypes: [HAS_ATTACK_PATH]
            after: $after)
            {
            nodes {
                primaryDisplayName
                secondaryDisplayName
                riskScoreSeverity
                type
                accounts {
                    enabled
                }
                riskFactors {
                    type
                    ... on AttackPathBasedRiskFactor {
                        attackPath {
                            entity {
                                primaryDisplayName
                                secondaryDisplayName
                                type
                                riskScoreSeverity
                                accounts {
                                    enabled
                                }
                            }
                            relation
                            nextEntity {
                                primaryDisplayName
                                secondaryDisplayName
                                type
                                riskScoreSeverity
                                accounts {
                                    enabled
                                }
                            }
                        }
                    }
                }
            }
            pageInfo {
                hasNextPage
                endCursor
            }
            }
        }
        """

    else:
        domains_include_str = json.dumps(dom_pattern)[1:-1] # create a string of domains to include from the list

        query = """
        query ($after: Cursor)
        {
            entities(
            archived: false
            first: 1000
            domains: [%s]
            riskFactorTypes: [HAS_ATTACK_PATH]
            after: $after)
            {
            nodes {
                primaryDisplayName
                secondaryDisplayName
                riskScoreSeverity
                type
                accounts {
                    enabled
                }
                riskFactors {
                    type
                    ... on AttackPathBasedRiskFactor {
                        attackPath {
                            entity {
                                primaryDisplayName
                                secondaryDisplayName
                                type
                                riskScoreSeverity
                                accounts {
                                    enabled
                                }
                            }
                            relation
                            nextEntity {
                                primaryDisplayName
                                secondaryDisplayName
                                type
                                riskScoreSeverity
                                accounts {
                                    enabled
                                }
                            }
                        }
                    }
                }
            }
            pageInfo {
                hasNextPage
                endCursor
            }
            }
        }
        """ % (domains_include_str)


    # Query for the Data:
    nodes = queryData(baseurl, query, client, secret)

    # Now to export the data to XLSX
    xlsx_file_name = "IDP_AttackPathData_" + str(datetime.now(timezone.utc).strftime('%Y_%m_%d-%H-%M-%S')) + ".xlsx"
    all_ap, summary_ap, steps_ap = parseNodesForExport(nodes)
    notated_steps_ap = findAPGoodies(steps_ap)
    # All AP Data
    all_ap_data = {
        "Entities With Attack Paths": all_ap,
        "Attack Path Summary": summary_ap,
        "Attack Path Steps Expanded": notated_steps_ap
    }
    all_ap_headers = {
        "Entities With Attack Paths": ['Starting Entity', 'Starting Entity Type', 'Starting Entity Enabled', 'Destination Entity', 'Destination Entity Type', 'Destination Entity Enabled', 'AttackPath Steps', 'Relations', 'Details'],
        "Attack Path Summary": ['Starting Entity', 'Starting Entity Type', 'Starting Entity Enabled', 'Destination Entity', 'Destination Entity Type', 'Destination Entity Enabled', 'AttackPath Steps', 'Relations', 'Details', 'Total Similar Paths', 'Entities With Similar Paths'],
        "Attack Path Steps Expanded": ['AP Start (Type)', 'AP Destination (Type)', 'Step Starting Entity', 'Step Starting Entity Type', 'Step Relation', 'Step Destination Entity', 'Step Destination Entity Type', 'Notes']
    }
    
    # Export the data:
    exportXLSX(all_ap_data, all_ap_headers, xlsx_file_name, output_dir)

    # Exit the script
    exit(0)

if __name__ == '__main__':
  main()
