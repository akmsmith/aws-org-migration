import boto3
import json
import re
from botocore.exceptions import ClientError

def get_account_id():
    sts = boto3.client('sts')
    return sts.get_caller_identity()['Account']

def get_org_id():
    try:
        org = boto3.client('organizations')
        response = org.describe_organization()
        return response['Organization']['Id']
    except ClientError as e:
        print("Warning: Could not retrieve Organization ID. Are you in an AWS Organization?")
        return None

def get_enabled_regions():
    ec2 = boto3.client('ec2')
    response = ec2.describe_regions(AllRegions=False)
    return [r['RegionName'] for r in response['Regions'] if r.get('OptInStatus') in ('opt-in-not-required', 'opted-in')]

def get_kms_keys(region_name):
    kms = boto3.client('kms', region_name=region_name)
    paginator = kms.get_paginator('list_keys')
    keys = []
    for page in paginator.paginate():
        keys.extend(page['Keys'])
    return keys

def get_key_policy(kms, key_id):
    response = kms.get_key_policy(KeyId=key_id, PolicyName='default')
    return json.loads(response['Policy'])

def is_cross_account(principal, my_account_id):
    arn_pattern = r'arn:aws:iam::(\d+):'
    if isinstance(principal, str):
        match = re.match(arn_pattern, principal)
        return match and match.group(1) != my_account_id
    elif isinstance(principal, list):
        return any(is_cross_account(p, my_account_id) for p in principal)
    elif isinstance(principal, dict):
        return any(is_cross_account(v, my_account_id) for v in principal.values())
    return False

def is_cross_org(statement, my_org_id):
    if not my_org_id:
        return False
    condition = statement.get('Condition', {})
    for key, value in condition.items():
        if 'aws:PrincipalOrgID' in value:
            if isinstance(value['aws:PrincipalOrgID'], str):
                return value['aws:PrincipalOrgID'] != my_org_id
            elif isinstance(value['aws:PrincipalOrgID'], list):
                return any(org_id != my_org_id for org_id in value['aws:PrincipalOrgID'])
    return False

def main():
    my_account_id = get_account_id()
    my_org_id = get_org_id()
    print(f"Detected AWS Account ID: {my_account_id}")
    if my_org_id:
        print(f"Detected AWS Organization ID: {my_org_id}")
    else:
        print("No AWS Organization detected or insufficient permissions.")

    regions = get_enabled_regions()
    print(f"Enabled regions: {regions}")

    total_keys = 0
    cross_account_findings = []
    cross_org_findings = []

    for region in regions:
        print(f"\nChecking region: {region}")
        kms = boto3.client('kms', region_name=region)
        keys = get_kms_keys(region)
        print(f"  Found {len(keys)} KMS keys.")
        total_keys += len(keys)
        for key in keys:
            key_id = key['KeyId']
            try:
                policy = get_key_policy(kms, key_id)
            except Exception as e:
                print(f"    Could not get policy for key {key_id}: {e}")
                continue
            for statement in policy.get('Statement', []):
                principal = statement.get('Principal', {}).get('AWS')
                if principal and is_cross_account(principal, my_account_id):
                    finding = f"    [Cross-Account] KMS Key {key_id} in {region} has cross-account access: {principal}"
                    print(finding)
                    cross_account_findings.append(finding)
                if is_cross_org(statement, my_org_id):
                    finding = f"    [Cross-Org] KMS Key {key_id} in {region} has cross-organization access: {statement.get('Condition')}"
                    print(finding)
                    cross_org_findings.append(finding)

    print("\n=== SUMMARY ===")
    print(f"Total regions checked: {len(regions)}")
    print(f"Total KMS keys checked: {total_keys}")
    print(f"Cross-account findings: {len(cross_account_findings)}")
    print(f"Cross-organization findings: {len(cross_org_findings)}")

    if not cross_account_findings and not cross_org_findings:
        print("No cross-account or cross-organization access detected in any KMS key policies.")

if __name__ == "__main__":
    main()