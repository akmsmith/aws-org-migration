import boto3

org = boto3.client('organizations')

# Get all delegated administrators
delegated_admins = org.list_delegated_administrators()['DelegatedAdministrators']

print("Delegated Administrator Accounts and Their Services:")
for admin in delegated_admins:
    account_id = admin['Id']
    account_email = admin['Email']
    print(f"\nAccount ID: {account_id} | Email: {account_email}")
    # List delegated services for this account
    services = org.list_delegated_services_for_account(AccountId=account_id)['DelegatedServices']
    if services:
        for svc in services:
            print(f"  - Service: {svc['ServicePrincipal']}")
    else:
        print("  - No delegated services found.")