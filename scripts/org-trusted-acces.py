import boto3

def list_trusted_services():
    client = boto3.client('organizations')
    trusted_services = []
    next_token = None

    while True:
        if next_token:
            response = client.list_aws_service_access_for_organization(NextToken=next_token)
        else:
            response = client.list_aws_service_access_for_organization()
        
        trusted_services.extend(response.get('EnabledServicePrincipals', []))
        next_token = response.get('NextToken')
        if not next_token:
            break

    print("Services with trusted access enabled:")
    for service in trusted_services:
        print(f"- Service Principal: {service['ServicePrincipal']}, Enabled At: {service['DateEnabled']}")

if __name__ == "__main__":
    list_trusted_services()