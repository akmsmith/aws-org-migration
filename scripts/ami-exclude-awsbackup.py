import boto3

def get_enabled_regions():
    ec2 = boto3.client('ec2')
    regions = ec2.describe_regions()['Regions']
    enabled_regions = [
        region['RegionName']
        for region in regions
        if region.get('OptInStatus') in ('opt-in-not-required', 'opted-in')
    ]
    return enabled_regions

def is_aws_backup_ami(image):
    # Check for AWS Backup tag
    tags = {tag['Key']: tag['Value'] for tag in image.get('Tags', [])}
    if 'aws:backup:source-resource' in tags:
        return True
    # Optionally, check description for AWS Backup
    if 'Description' in image and 'AWS Backup' in image['Description']:
        return True
    return False

def audit_amis_in_region(region_name, account_id):
    ec2 = boto3.client('ec2', region_name=region_name)
    images = ec2.describe_images(Owners=[account_id])['Images']
    results = []
    for image in images:
        # Skip AWS Backup-created AMIs
        if is_aws_backup_ami(image):
            continue
        ami_id = image['ImageId']
        perms = ec2.describe_image_attribute(ImageId=ami_id, Attribute='launchPermission')
        shared_accounts = []
        is_public = False

        for perm in perms.get('LaunchPermissions', []):
            if 'UserId' in perm:
                shared_accounts.append(perm['UserId'])
            if perm.get('Group') == 'all':
                is_public = True

        if shared_accounts or is_public:
            result = f"[{region_name}] AMI {ami_id} is shared:"
            if shared_accounts:
                result += f"\n  With accounts: {', '.join(shared_accounts)}"
            if is_public:
                result += "\n  Publicly accessible!"
            results.append(result)
    return results

def main():
    account_id = boto3.client('sts').get_caller_identity()['Account']
    regions = get_enabled_regions()
    found_any = False
    all_results = []
    for region in regions:
        results = audit_amis_in_region(region, account_id)
        if results:
            found_any = True
            all_results.extend(results)
    if found_any:
        for result in all_results:
            print(result)
    else:
        print("No AMIs with cross-account or public permissions found in any active region.")

if __name__ == "__main__":
    main()