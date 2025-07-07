import boto3

def list_enabled_policy_types():
    client = boto3.client('organizations')

    # Get the root ID and policy types of the organization
    roots = client.list_roots()
    root = roots['Roots'][0]
    root_id = root['Id']

    # Get enabled policy types for the root
    policy_types = root.get('PolicyTypes', [])

    enabled_types = [pt['Type'] for pt in policy_types if pt['Status'] == 'ENABLED']

    print("Enabled AWS Organizations Policy Types:")
    for policy_type in enabled_types:
        print(f"- {policy_type}")

if __name__ == "__main__":
    list_enabled_policy_types()