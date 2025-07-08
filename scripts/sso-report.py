import boto3
import pandas as pd
from botocore.exceptions import ClientError

def get_enabled_regions():
    ec2 = boto3.client('ec2')
    regions = ec2.describe_regions(AllRegions=False)
    return [r['RegionName'] for r in regions['Regions']]

def list_sso_instances(sso_admin):
    instances = []
    paginator = sso_admin.get_paginator('list_instances')
    for page in paginator.paginate():
        instances.extend(page['Instances'])
    return instances

def get_identity_provider_info(sso_admin, instance_arn):
    try:
        response = sso_admin.describe_instance(InstanceArn=instance_arn)
        # Possible values: 'AWS_MANAGED', 'IDENTITY_STORE', 'EXTERNAL_IDP', 'AD_CONNECTOR'
        provider_type = response.get('IdentityStoreType', 'Unknown')
        # For EXTERNAL_IDP, you can also get the provider name if available
        provider_details = response.get('IdentityStoreProperties', {})
        return provider_type, provider_details
    except Exception as e:
        return 'Unknown', {}

def main():
    session = boto3.Session()
    org_client = session.client('organizations')
    identitystore = session.client('identitystore')

    # Discover all enabled regions
    regions = get_enabled_regions()
    print("Enabled AWS regions:", regions)

    report_rows = []

    for region in regions:
        print(f"Checking region: {region}")
        sso_admin = session.client('sso-admin', region_name=region)
        try:
            sso_instances = list_sso_instances(sso_admin)
        except ClientError as e:
            print(f"Could not query SSO in {region}: {e}")
            continue

        if not sso_instances:
            continue

        for instance in sso_instances:
            instance_arn = instance['InstanceArn']
            identity_store_id = instance['IdentityStoreId']

            # Get identity provider info
            provider_type, provider_details = get_identity_provider_info(sso_admin, instance_arn)
            print(f"Found SSO instance in {region}: {instance_arn} (Provider: {provider_type})")

            # Example: List permission sets for this instance
            paginator = sso_admin.get_paginator('list_permission_sets')
            permission_sets = []
            for page in paginator.paginate(InstanceArn=instance_arn):
                permission_sets.extend(page['PermissionSets'])

            # Example: List accounts in the org
            accounts = []
            paginator = org_client.get_paginator('list_accounts')
            for page in paginator.paginate():
                accounts.extend(page['Accounts'])

            # Example: For each account and permission set, list assignments
            for account in accounts:
                account_id = account['Id']
                account_name = account['Name']
                for ps_arn in permission_sets:
                    paginator = sso_admin.get_paginator('list_account_assignments')
                    for page in paginator.paginate(
                        InstanceArn=instance_arn,
                        AccountId=account_id,
                        PermissionSetArn=ps_arn
                    ):
                        for assignment in page['AccountAssignments']:
                            principal_type = assignment['PrincipalType']
                            principal_id = assignment['PrincipalId']
                            # Look up user/group name
                            try:
                                if principal_type == 'USER':
                                    user = identitystore.describe_user(
                                        IdentityStoreId=identity_store_id,
                                        UserId=principal_id
                                    )
                                    principal_name = user['UserName']
                                elif principal_type == 'GROUP':
                                    group = identitystore.describe_group(
                                        IdentityStoreId=identity_store_id,
                                        GroupId=principal_id
                                    )
                                    principal_name = group['DisplayName']
                                else:
                                    principal_name = 'Unknown'
                            except Exception:
                                principal_name = 'Unknown'
                            report_rows.append({
                                'Region': region,
                                'InstanceArn': instance_arn,
                                'IdentityProviderType': provider_type,
                                'IdentityProviderDetails': str(provider_details),
                                'AccountId': account_id,
                                'AccountName': account_name,
                                'PermissionSetArn': ps_arn,
                                'PrincipalType': principal_type,
                                'PrincipalName': principal_name
                            })

    if report_rows:
        df = pd.DataFrame(report_rows)
        df.to_csv('aws_sso_report_all_regions_with_idp.csv', index=False)
        print("Report generated: aws_sso_report_all_regions_with_idp.csv")
    else:
        print("No SSO instances found in any region.")

if __name__ == "__main__":
    main()
