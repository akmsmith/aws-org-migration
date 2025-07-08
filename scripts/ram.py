import boto3

def get_active_regions():
    ec2 = boto3.client('ec2')
    response = ec2.describe_regions(AllRegions=False)
    regions = [region['RegionName'] for region in response['Regions']]
    return regions

def list_ram_resources_in_active_regions():
    session = boto3.Session()
    active_regions = get_active_regions()
    all_resources = []

    for region in active_regions:
        print(f"Scanning region: {region}")
        ram = session.client('ram', region_name=region)
        next_token = None

        while True:
            params = {'resourceOwner': 'SELF'}
            if next_token:
                params['nextToken'] = next_token

            response = ram.list_resources(**params)
            all_resources.extend(response.get('resources', []))
            next_token = response.get('nextToken')
            if not next_token:
                break

    return all_resources

if __name__ == "__main__":
    ram_resources = list_ram_resources_in_active_regions()
    for resource in ram_resources:
        print(f"Resource ARN: {resource['arn']}, Type: {resource['type']}, Region: {resource.get('regionScope')}")