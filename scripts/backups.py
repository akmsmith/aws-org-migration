import boto3
from botocore.exceptions import ClientError

def get_all_regions():
    """Retrieve all enabled AWS regions for the Backup service."""
    ec2 = boto3.client('ec2')
    regions = ec2.describe_regions(AllRegions=False)
    return [region['RegionName'] for region in regions['Regions']]

def list_cross_account_backups(region, account_id):
    """List cross-account backups in a given region."""
    client = boto3.client('backup', region_name=region)
    try:
        vaults = client.list_backup_vaults()['BackupVaultList']
    except ClientError as e:
        print(f"  Could not access Backup in {region}: {e}")
        return

    if not vaults:
        print(f"\nRegion: {region} | No backup vaults found.")
        return

    for vault in vaults:
        vault_name = vault['BackupVaultName']
        cross_account_found = False
        print(f"\nRegion: {region} | Vault: {vault_name}")
        paginator = client.get_paginator('list_recovery_points_by_backup_vault')
        for page in paginator.paginate(BackupVaultName=vault_name):
            for rp in page['RecoveryPoints']:
                source_account = rp.get('SourceAccountId')
                if source_account and source_account != account_id:
                    cross_account_found = True
                    print(f"  Cross-account backup found:")
                    print(f"    RecoveryPointArn: {rp['RecoveryPointArn']}")
                    print(f"    SourceAccountId: {source_account}")
                    print(f"    CreationDate: {rp['CreationDate']}")
        if not cross_account_found:
            print("  No cross-account backups found in this vault.")

def main():
    # Get current account ID
    sts = boto3.client('sts')
    account_id = sts.get_caller_identity()['Account']

    # Get all active regions
    regions = get_all_regions()
    print(f"Found {len(regions)} active regions: {regions}")

    for region in regions:
        list_cross_account_backups(region, account_id)

if __name__ == "__main__":
    main()