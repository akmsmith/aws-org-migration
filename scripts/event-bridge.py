import boto3
import json

def get_account_id():
    sts = boto3.client('sts')
    return sts.get_caller_identity()['Account']

def get_org_id():
    try:
        org = boto3.client('organizations')
        return org.describe_organization()['Organization']['Id']
    except Exception:
        return None  # Not in an organization

def list_event_buses(region):
    client = boto3.client('events', region_name=region)
    buses = client.list_event_buses()['EventBuses']
    return [bus['Name'] for bus in buses]

def get_event_bus_policy(client, bus_name):
    try:
        response = client.describe_event_bus(Name=bus_name)
        policy = response.get('Policy')
        if policy:
            return json.loads(policy)
    except client.exceptions.ResourceNotFoundException:
        pass
    return None

def is_cross_account_statement(statement, account_id, org_id):
    principals = statement.get('Principal')
    condition = statement.get('Condition', {})
    # Check for AWS account principal
    if principals and 'AWS' in principals:
        aws_principals = principals['AWS']
        if isinstance(aws_principals, str):
            aws_principals = [aws_principals]
        for arn in aws_principals:
            if account_id not in arn:
                return True
    # Check for organization-wide access
    if 'StringEquals' in condition and 'aws:PrincipalOrgID' in condition['StringEquals']:
        if org_id and condition['StringEquals']['aws:PrincipalOrgID'] == org_id:
            return True
    return False

def main():
    session = boto3.Session()
    account_id = get_account_id()
    org_id = get_org_id()
    regions = [r['RegionName'] for r in boto3.client('ec2').describe_regions()['Regions']]

    for region in regions:
        print(f"\nRegion: {region}")
        client = boto3.client('events', region_name=region)
        bus_names = list_event_buses(region)
        for bus_name in bus_names:
            policy = get_event_bus_policy(client, bus_name)
            if not policy:
                continue
            statements = policy.get('Statement', [])
            for stmt in statements:
                if is_cross_account_statement(stmt, account_id, org_id):
                    print(f"  Event bus '{bus_name}' has cross-account or org policy:")
                    print(json.dumps(stmt, indent=2))

if __name__ == "__main__":
    main()