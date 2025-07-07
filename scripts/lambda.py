import boto3
import json
import re

def is_cross_account(principal, org_account_ids=None):
    if principal == "*" or principal == {"AWS": "*"}:
        return True
    if isinstance(principal, dict) and "AWS" in principal:
        aws_principal = principal["AWS"]
        if isinstance(aws_principal, list):
            return any(is_cross_account(p, org_account_ids) for p in aws_principal)
        m = re.match(r"arn:aws:iam::(\d{12}):root", aws_principal)
        if m:
            account_id = m.group(1)
            if org_account_ids and account_id in org_account_ids:
                return False
            return True
    return False

def get_all_regions():
    ec2 = boto3.client('ec2')
    regions = ec2.describe_regions(AllRegions=False)
    return [r['RegionName'] for r in regions['Regions']]

def main():
    regions = get_all_regions()
    for region in regions:
        print(f"Checking region: {region}")
        lambda_client = boto3.client('lambda', region_name=region)
        paginator = lambda_client.get_paginator('list_functions')
        try:
            for page in paginator.paginate():
                for function in page['Functions']:
                    fn_name = function['FunctionName']
                    try:
                        policy_response = lambda_client.get_policy(FunctionName=fn_name)
                        policy = json.loads(policy_response['Policy'])
                        for stmt in policy.get('Statement', []):
                            principal = stmt.get('Principal')
                            if is_cross_account(principal):
                                print(f"Region: {region} | Function: {fn_name} | Cross-account/org policy: {json.dumps(stmt)}")
                    except lambda_client.exceptions.ResourceNotFoundException:
                        continue  # No policy attached
                    except Exception as e:
                        print(f"Error processing function {fn_name} in {region}: {e}")
        except Exception as e:
            print(f"Error listing functions in region {region}: {e}")

if __name__ == "__main__":
    main()