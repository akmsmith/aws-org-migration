import boto3
from botocore.exceptions import ClientError

def get_enabled_regions():
    ec2 = boto3.client('ec2', region_name='us-east-1')
    regions = ec2.describe_regions(AllRegions=True)
    enabled = [
        r['RegionName']
        for r in regions['Regions']
        if r['OptInStatus'] in ('opt-in-not-required', 'opted-in')
    ]
    return enabled

def check_config(region):
    client = boto3.client('config', region_name=region)
    try:
        recorders = client.describe_configuration_recorders()
        return len(recorders.get('ConfigurationRecorders', [])) > 0
    except ClientError:
        return False

def check_securityhub(region):
    client = boto3.client('securityhub', region_name=region)
    try:
        status = client.get_findings()
        return True
    except ClientError as e:
        if e.response['Error']['Code'] in ['InvalidAccessException', 'AccessDeniedException', 'InvalidInputException', 'ResourceNotFoundException']:
            return False
        return False

def check_guardduty(region):
    client = boto3.client('guardduty', region_name=region)
    try:
        detectors = client.list_detectors()
        return len(detectors.get('DetectorIds', [])) > 0
    except ClientError:
        return False

def get_cloudtrails(region):
    client = boto3.client('cloudtrail', region_name=region)
    try:
        trails = client.describe_trails(includeShadowTrails=False)
        # Only custom trails (not shadow trails)
        custom_trails = [t['Name'] for t in trails.get('trailList', []) if not t.get('IsOrganizationTrail', False)]
        return custom_trails
    except ClientError:
        return []

def main():
    regions = get_enabled_regions()
    print(f"Checking {len(regions)} enabled regions...")
    results = []

    for region in regions:
        config_enabled = check_config(region)
        securityhub_enabled = check_securityhub(region)
        guardduty_enabled = check_guardduty(region)
        cloudtrails = get_cloudtrails(region)

        results.append({
            'Region': region,
            'Config': config_enabled,
            'SecurityHub': securityhub_enabled,
            'GuardDuty': guardduty_enabled,
            'CloudTrails': cloudtrails
        })

    print("\nSummary:")
    for r in results:
        cloudtrail_names = ', '.join(r['CloudTrails']) if r['CloudTrails'] else 'None'
        print(
            f"{r['Region']}: Config={'Yes' if r['Config'] else 'No'}, "
            f"SecurityHub={'Yes' if r['SecurityHub'] else 'No'}, "
            f"GuardDuty={'Yes' if r['GuardDuty'] else 'No'}, "
            f"CloudTrails={cloudtrail_names}"
        )

if __name__ == "__main__":
    main()