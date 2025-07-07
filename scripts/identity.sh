#!/bin/bash

echo "Starting IAM Identity Center and Identity Provider Check..."

# IAM Identity Center (AWS SSO)
echo "Checking for IAM Identity Center (AWS SSO) instance..."
RAW_SSO_OUTPUT=$(aws sso-admin list-instances 2>&1)
echo "Raw output from 'aws sso-admin list-instances':"
echo "$RAW_SSO_OUTPUT"

IDENTITY_CENTER_INSTANCE=$(echo "$RAW_SSO_OUTPUT" | grep InstanceArn | head -1 | awk -F'"' '{print $4}')

if [[ -z "$IDENTITY_CENTER_INSTANCE" ]]; then
    echo "IAM Identity Center is NOT enabled in this account."
else
    echo "IAM Identity Center is ENABLED."
    echo "Instance ARN: $IDENTITY_CENTER_INSTANCE"
fi

echo ""
echo "Checking for SAML identity providers..."
RAW_SAML_OUTPUT=$(aws iam list-saml-providers 2>&1)
echo "Raw output from 'aws iam list-saml-providers':"
echo "$RAW_SAML_OUTPUT"

SAML_PROVIDERS=$(echo "$RAW_SAML_OUTPUT" | grep arn:aws:iam | awk '{print $2}' | tr -d '",')

if [[ -z "$SAML_PROVIDERS" ]]; then
    echo "No SAML providers found."
else
    echo "SAML Providers:"
    echo "$SAML_PROVIDERS"
fi

echo ""
echo "Checking for OIDC identity providers..."
RAW_OIDC_OUTPUT=$(aws iam list-open-id-connect-providers 2>&1)
echo "Raw output from 'aws iam list-open-id-connect-providers':"
echo "$RAW_OIDC_OUTPUT"

OIDC_PROVIDERS=$(echo "$RAW_OIDC_OUTPUT" | grep arn:aws:iam | awk '{print $2}' | tr -d '",')

if [[ -z "$OIDC_PROVIDERS" ]]; then
    echo "No OIDC providers found."
else
    echo "OIDC Providers:"
    echo "$OIDC_PROVIDERS"
fi

echo ""
echo "Script completed."

# Diagnostic suggestion if all are empty
if [[ -z "$IDENTITY_CENTER_INSTANCE" && -z "$SAML_PROVIDERS" && -z "$OIDC_PROVIDERS" ]]; then
    echo ""
    echo "NOTE: All outputs are empty. This usually means:"
    echo " - IAM Identity Center is not enabled."
    echo " - No SAML or OIDC identity providers are configured."
    echo " - Or, your AWS CLI credentials do not have permission to view these resources."
    echo ""
    echo "Try running 'aws sts get-caller-identity' to confirm your AWS CLI is configured and working."
fi