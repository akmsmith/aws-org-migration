import boto3
import json

def get_current_account_and_org():
    sts = boto3.client('sts')
    org = boto3.client('organizations')
    account_id = sts.get_caller_identity()['Account']
    try:
        org_id = org.describe_organization()['Organization']['Id']
    except Exception:
        org_id = None  # Not in an organization
    return account_id, org_id

def extract_account_id_from_arn(arn):
    # arn:aws:iam::123456789012:role/SomeRole
    parts = arn.split(':')
    if len(parts) > 4:
        return parts[4]
    return None

def extract_org_id_from_arn(arn):
    # arn:aws:iam::123456789012:role/SomeRole
    # arn:aws:iam::123456789012:role/OrganizationAccountAccessRole
    # arn:aws:organizations::123456789012:organization/o-xxxxxxxxxx
    if ":organization/" in arn:
        return arn.split("/")[-1]
    return None

def is_cross_account(principal, current_account_id):
    if isinstance(principal, str):
        return principal != f"arn:aws:iam::{current_account_id}:root"
    elif isinstance(principal, list):
        return any(is_cross_account(p, current_account_id) for p in principal)
    elif isinstance(principal, dict):
        return any(is_cross_account(p, current_account_id) for p in principal.values())
    return False

def main():
    current_account_id, current_org_id = get_current_account_and_org()
    iam = boto3.client('iam')
    paginator = iam.get_paginator('list_roles')
    print(f"Current Account: {current_account_id}, Organization: {current_org_id}")
    for response in paginator.paginate():
        for role in response['Roles']:
            role_name = role['RoleName']
            assume_policy = role['AssumeRolePolicyDocument']
            for stmt in assume_policy.get('Statement', []):
                if stmt.get('Effect') != 'Allow':
                    continue
                principal = stmt.get('Principal', {}).get('AWS')
                if not principal:
                    continue
                # Normalize to list
                if isinstance(principal, str):
                    principal = [principal]
                for arn in principal:
                    if arn.startswith("arn:aws:iam::"):
                        acct_id = extract_account_id_from_arn(arn)
                        if acct_id and acct_id != current_account_id:
                            print(f"Role '{role_name}' can be assumed by account {acct_id} (cross-account)")
                    elif arn.startswith("arn:aws:organizations::"):
                        org_id = extract_org_id_from_arn(arn)
                        if org_id and org_id != current_org_id:
                            print(f"Role '{role_name}' can be assumed by organization {org_id} (cross-organization)")
                        elif org_id and org_id == current_org_id:
                            print(f"Role '{role_name}' can be assumed by another account in this organization (cross-org, same org)")

if __name__ == "__main__":
    main()