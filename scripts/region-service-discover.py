import boto3
from datetime import datetime, timedelta

# Initialize Cost Explorer client
client = boto3.client('ce')

# Define the time period (last full month)
end = datetime.today().replace(day=1)
start = (end - timedelta(days=1)).replace(day=1)

# Step 1: Find top 5 regions by cost
response = client.get_cost_and_usage(
    TimePeriod={
        'Start': start.strftime('%Y-%m-%d'),
        'End': end.strftime('%Y-%m-%d')
    },
    Granularity='MONTHLY',
    Metrics=['UnblendedCost'],
    GroupBy=[
        {'Type': 'DIMENSION', 'Key': 'REGION'}
    ]
)

region_costs = []
for group in response['ResultsByTime'][0]['Groups']:
    region = group['Keys'][0]
    cost = float(group['Metrics']['UnblendedCost']['Amount'])
    region_costs.append((region, cost))

top_regions = sorted(region_costs, key=lambda x: x[1], reverse=True)[:5]

print("Top 5 Most Active AWS Regions (by cost):")
for rank, (region, cost) in enumerate(top_regions, 1):
    print(f"{rank}. {region}: ${cost:.2f}")

# Step 2: For each top region, find top services
print("\nTop Services by Cost in Each Region:")
for region, _ in top_regions:
    service_response = client.get_cost_and_usage(
        TimePeriod={
            'Start': start.strftime('%Y-%m-%d'),
            'End': end.strftime('%Y-%m-%d')
        },
        Granularity='MONTHLY',
        Metrics=['UnblendedCost'],
        Filter={
            'Dimensions': {
                'Key': 'REGION',
                'Values': [region]
            }
        },
        GroupBy=[
            {'Type': 'DIMENSION', 'Key': 'SERVICE'}
        ]
    )
    service_costs = []
    for group in service_response['ResultsByTime'][0]['Groups']:
        service = group['Keys'][0]
        cost = float(group['Metrics']['UnblendedCost']['Amount'])
        service_costs.append((service, cost))
    top_services = sorted(service_costs, key=lambda x: x[1], reverse=True)[:5]

    print(f"\nRegion: {region}")
    for idx, (service, cost) in enumerate(top_services, 1):
        print(f"  {idx}. {service}: ${cost:.2f}")