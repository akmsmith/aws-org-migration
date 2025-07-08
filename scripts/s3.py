import boto3
import json
from botocore.exceptions import ClientError

def is_cross_account_or_org_policy(statement, current_account):
    # Check for cross-account or organization permissions in bucket policy
    if 'Principal' in statement:
        principal = statement['Principal']
        if isinstance(principal, dict):
            aws_principal = principal.get('AWS')
            if isinstance(aws_principal, list):
                for arn in aws_principal:
                    if f":{current_account}:" not in arn:
                        return True
            elif isinstance(aws_principal, str):
                if f":{current_account}:" not in aws_principal:
                    return True
        elif principal == "*":
            # Public, not cross-account, skip
            return False
    if 'Condition' in statement:
        condition = statement['Condition']
        for cond in condition.values():
            if isinstance(cond, dict):
                for key in cond:
                    if key == "aws:PrincipalOrgID":
                        return True
    return False

def is_cross_account_acl(grants, current_owner_id):
    findings = []
    for grant in grants:
        grantee = grant.get('Grantee', {})
        if grantee.get('Type') == 'CanonicalUser':
            if grantee.get('ID') and grantee.get('ID') != current_owner_id:
                findings.append(f"CanonicalUser: {grantee.get('ID')}")
        elif grantee.get('Type') == 'Group':
            uri = grantee.get('URI', '')
            if uri in [
                "http://acs.amazonaws.com/groups/global/AllUsers",
                "http://acs.amazonaws.com/groups/global/AuthenticatedUsers"
            ]:
                findings.append(f"Group: {uri}")
    return findings

def main():
    s3 = boto3.client('s3')
    sts = boto3.client('sts')
    current_account = sts.get_caller_identity()['Account']

    buckets = s3.list_buckets()['Buckets']
    total_buckets = len(buckets)
    findings_found = False

    print("Scanning S3 buckets for cross-account and organization permissions...\n")
    for bucket in buckets:
        bucket_name = bucket['Name']
        bucket_findings = []

        # Check bucket policy
        try:
            policy_str = s3.get_bucket_policy(Bucket=bucket_name)['Policy']
            policy = json.loads(policy_str)
            for statement in policy.get('Statement', []):
                if is_cross_account_or_org_policy(statement, current_account):
                    bucket_findings.append("  [!] Cross-account or organization permission in bucket policy:\n" +
                                          json.dumps(statement, indent=2))
        except ClientError as e:
            if e.response['Error']['Code'] != 'NoSuchBucketPolicy':
                bucket_findings.append(f"  Error accessing policy: {e}")

        # Check bucket ACL
        try:
            acl = s3.get_bucket_acl(Bucket=bucket_name)
            findings = is_cross_account_acl(acl['Grants'], acl['Owner']['ID'])
            if findings:
                bucket_findings.append("  [!] Cross-account or group permissions in bucket ACL:\n" +
                                      "\n".join([f"      - {f}" for f in findings]))
        except ClientError as e:
            bucket_findings.append(f"  Error accessing bucket ACL: {e}")

        # Check object ACLs (sampled: first 1000 objects)
        try:
            paginator = s3.get_paginator('list_objects_v2')
            for page in paginator.paginate(Bucket=bucket_name, PaginationConfig={'MaxItems': 1000}):
                for obj in page.get('Contents', []):
                    key = obj['Key']
                    try:
                        obj_acl = s3.get_object_acl(Bucket=bucket_name, Key=key)
                        obj_findings = is_cross_account_acl(obj_acl['Grants'], obj_acl['Owner']['ID'])
                        if obj_findings:
                            bucket_findings.append(
                                f"  [!] Object '{key}' has cross-account or group permissions in ACL:\n" +
                                "\n".join([f"      - {f}" for f in obj_findings])
                            )
                    except ClientError:
                        continue
                break  # Remove this break to scan all objects (may be slow)
        except ClientError as e:
            bucket_findings.append(f"  Error listing objects: {e}")

        if bucket_findings:
            findings_found = True
            print(f"\nBucket: {bucket_name}")
            for finding in bucket_findings:
                print(finding)

    print(f"\nScan complete. Buckets scanned: {total_buckets}")
    if not findings_found:
        print("No cross-account, organization, or group ACL findings detected in any bucket.")

if __name__ == "__main__":
    main()
