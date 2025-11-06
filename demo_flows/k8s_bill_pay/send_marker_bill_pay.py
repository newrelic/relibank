import requests
import os
import json
import secrets
import sys

# relibank_marker.py badCommit <user_key> <account_id> <env>

# TODO github variables
user_key = sys.argv[2]
account_id = sys.argv[3]
endpoints = {
    "staging": "https://nerd-graph.staging-service.nr-ops.net/graphql",
    "production": "https://api.newrelic.com/graphql"
}

def getFakeCommitHash():
    return secrets.token_hex(20)

def getEntityGuid(key, appname, environment):

    print(f"Getting entity guid for {appname}")

    payload = f"""
    {{
        actor {{
            account(id: {account_id}) {{
                nrql(query: "FROM Transaction SELECT entityGuid WHERE appName LIKE '%{appname}' LIMIT 1") {{
                    results
                }}
            }}
        }}
    }}
    """
    print(payload)

    # NerdGraph endpoint
    endpoint = endpoints[environment]
    headers = {'Content-Type': 'application/json', 'API-Key': f'{key}'}
    response = requests.post(endpoint, headers=headers, json={'query': payload})

    if response.status_code == 200:
        dict_response = json.loads(response.content)
        print(f"Success! Response: {dict_response}")
        entity_guid = dict_response['data']['actor']['account']['nrql']['results'][0]['entityGuid']
        # print(f"ENTITY GUID IS {entity_guid}")
    else:
        # raise an error with a HTTP response code
        print(response.content)
        raise Exception(f'NerdGraph query failed with a {response.status_code}.')
    return entity_guid

def sendMarkerEvent(category, type, commit, version, user, short_desc, desc, group_id, environment, guid):
    # user_key = self.environment.parsed_options.user_key
    # user_key = os.environ['new_relic_user_api_key']
    print(f"Sending deployment marker to guid {guid}")

    payload = f"""
    mutation {{
      changeTrackingCreateEvent(
        changeTrackingEvent: {{
          categoryAndTypeData: {{
            kind: {{ category: "{category}", type: "{type}" }}
            categoryFields: {{ deployment: {{ commit: "{commit}", version: "{version}" }} }}
          }}
          user: "{user}"
          shortDescription: "{short_desc}"
          description: "{desc}"
          groupId: "{group_id}"
          customAttributes: {{ environment: "{environment}" }}
          entitySearch: {{ query: "id = '{guid}'" }}
        }}
      ) {{
        changeTrackingEvent {{
          changeTrackingId
        }}
      }}
    }}
    """

    endpoint = endpoints[environment]
    headers = {'Content-Type': 'application/json', 'API-Key': f'{user_key}'}
    response = requests.post(endpoint, headers=headers, json={'query': payload})

    if response.status_code == 200:
        dict_response = json.loads(response.content)
        print(dict_response)
    else:
        print(response.content)
        # raise an error with a HTTP response code
        raise Exception(f'Nerdgraph request failed with a {response.status_code}.')
    return dict_response

if __name__ == '__main__':
    print("sanity check")
    marker_type = sys.argv[1]
    environment = sys.argv[4] if len(sys.argv) > 4 else "production"
    commit = getFakeCommitHash()

    if marker_type == "":
        print("please provide an argument, badCommit or goodCommit")
        exit(0)
        
    if marker_type == "badCommit":
        print("Sending commit with the bad image")
        category = "DEPLOYMENT"
        type = "ROLLING"
        version = "v0.4.01"
        user = "admin_access_token"
        short_desc = "Image deployment"
        desc = "Deploying new Bill Payment image"
        group_id = "NRDEMO-101423"
        guid = getEntityGuid(user_key, "Relibank - Bill Pay Service", environment)
        sendMarkerEvent(category, type, commit, version, user, short_desc, desc, group_id, environment, guid)

    elif marker_type == "goodCommit":
        print("Sending rollback commit")
        category = "DEPLOYMENT"
        type = "BASIC"
        version = "v0.4.02"
        user = "admin_access_token"
        short_desc = "Manual rollback deployment"
        desc = "ARGOCD: Reverting previous deployment"
        group_id = "NRDEMO-101423"
        guid = getEntityGuid(user_key, "Relibank - Bill Pay Service", environment)
        sendMarkerEvent(category, type, commit, version, user, short_desc, desc, group_id, environment, guid)

    else:
        print("bad input")
