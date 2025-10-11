"""
Utility functions for Snowflake MCP API
"""

import json
import boto3
from typing import Dict, Any, Optional
import boto3
import json
import time
from boto3.session import Session
import botocore
import requests
import os
import time



def get_secret(secret_name: str, region: str = "us-east-1") -> Dict[str, Any]:
    """
    Retrieve a secret from AWS Secrets Manager.
    
    Args:
        secret_name: The name or ARN of the secret to retrieve
        region: AWS region where the secret is stored (default: us-east-1)
    
    Returns:
        Dictionary containing the secret values
    
    Raises:
        ClientError: If the secret cannot be retrieved
    """
    sm = boto3.client("secretsmanager", region_name=region)
    response = sm.get_secret_value(SecretId=secret_name)
    return json.loads(response["SecretString"])


def format_query_results(rows: list, columns: Optional[list] = None) -> Dict[str, Any]:
    """
    Format Snowflake query results into a structured response.
    
    Args:
        rows: List of rows returned from Snowflake query
        columns: Optional list of column names
    
    Returns:
        Dictionary with formatted results
    """
    return {
        "row_count": len(rows),
        "columns": columns if columns else [],
        "data": rows
    }


def validate_connection_params(params: Dict[str, Any]) -> bool:
    """
    Validate that all required Snowflake connection parameters are present.
    
    Args:
        params: Dictionary of connection parameters
    
    Returns:
        True if all required parameters are present, False otherwise
    """
    required_params = ["user", "password", "account", "warehouse", "database", "schema"]
    return all(param in params for param in required_params)


def sanitize_query(query: str) -> str:
    """
    Basic query sanitization to prevent common SQL injection patterns.
    
    Args:
        query: SQL query string
    
    Returns:
        Sanitized query string
    
    Note:
        This is a basic implementation. Use parameterized queries for production.
    """
    # Remove common dangerous patterns
    dangerous_keywords = ["DROP", "DELETE", "TRUNCATE", "ALTER", "CREATE"]
    query_upper = query.upper()
    
    for keyword in dangerous_keywords:
        if keyword in query_upper:
            raise ValueError(f"Query contains potentially dangerous keyword: {keyword}")
    
    return query.strip()

def create_gateway_lambda(lambda_function_code_path) -> dict[str, int]:
    boto_session = Session()
    region = boto_session.region_name

    return_resp = {"lambda_function_arn": "Pending", "exit_code": 1}
    
    # Initialize clients
    lambda_client = boto3.client('lambda', region_name=region)
    iam_client = boto3.client('iam', region_name=region)

    # Use existing lambda-snowflake-role
    role_arn = 'arn:aws:iam::761018845710:role/lambda-snowflake-role'
    lambda_function_name = 'snowflakeMCPAPILambda'

    print(f"Using existing IAM role: {role_arn}")

    print("Reading code from zip file")
    with open(lambda_function_code_path, 'rb') as f:
        lambda_function_code = f.read()

    if role_arn != "":
        print("Creating lambda function")
        # Create lambda function    
        try:
            lambda_response = lambda_client.create_function(
                FunctionName=lambda_function_name,
                Role=role_arn,
                Runtime='python3.13',
                Handler='lambda_function_code.lambda_handler',
                Code = {'ZipFile': lambda_function_code},
                Description='Lambda function example for Bedrock AgentCore Gateway',
                PackageType='Zip'
            )

            return_resp['lambda_function_arn'] = lambda_response['FunctionArn']
            return_resp['exit_code'] = 0
        except botocore.exceptions.ClientError as error:
            if error.response['Error']['Code'] == "ResourceConflictException":
                response = lambda_client.get_function(FunctionName=lambda_function_name)
                lambda_arn = response['Configuration']['FunctionArn']
                print(f"AWS Lambda function {lambda_function_name} already exists. Using the same ARN {lambda_arn}")
                return_resp['lambda_function_arn'] = lambda_arn
                return_resp['exit_code'] = 0  # Success - Lambda exists
            else:
                error_message = error.response['Error']['Code'] + "-" + error.response['Error']['Message']
                print(f"Error creating lambda function: {error_message}")
                return_resp['lambda_function_arn'] = error_message

    return return_resp



def create_agentcore_gateway_role(gateway_name):
    iam_client = boto3.client('iam')
    agentcore_gateway_role_name = f'agentcore-{gateway_name}-role'
    boto_session = Session()
    region = boto_session.region_name
    account_id = boto3.client("sts").get_caller_identity()["Account"]
    role_policy = {
        "Version": "2012-10-17",
        "Statement": [{
                "Sid": "VisualEditor0",
                "Effect": "Allow",
                "Action": [
                    "bedrock-agentcore:*",
                    "bedrock:*",
                    "agent-credential-provider:*",
                    "iam:PassRole",
                    "secretsmanager:GetSecretValue",
                    "lambda:InvokeFunction"
                ],
                "Resource": "*"
            }
        ]
    }

    assume_role_policy_document = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Sid": "AssumeRolePolicy",
                "Effect": "Allow",
                "Principal": {
                    "Service": "bedrock-agentcore.amazonaws.com"
                },
                "Action": "sts:AssumeRole",
                "Condition": {
                    "StringEquals": {
                        "aws:SourceAccount": f"{account_id}"
                    },
                    "ArnLike": {
                        "aws:SourceArn": f"arn:aws:bedrock-agentcore:{region}:{account_id}:*"
                    }
                }
            }
        ]
    }

    assume_role_policy_document_json = json.dumps(
        assume_role_policy_document
    )

    role_policy_document = json.dumps(role_policy)
    # Create IAM Role for the Lambda function
    try:
        agentcore_iam_role = iam_client.create_role(
            RoleName=agentcore_gateway_role_name,
            AssumeRolePolicyDocument=assume_role_policy_document_json
        )

        # Pause to make sure role is created
        time.sleep(10)
    except iam_client.exceptions.EntityAlreadyExistsException:
        print("Role already exists -- deleting and creating it again")
        policies = iam_client.list_role_policies(
            RoleName=agentcore_gateway_role_name,
            MaxItems=100
        )
        print("policies:", policies)
        for policy_name in policies['PolicyNames']:
            iam_client.delete_role_policy(
                RoleName=agentcore_gateway_role_name,
                PolicyName=policy_name
            )
        print(f"deleting {agentcore_gateway_role_name}")
        iam_client.delete_role(
            RoleName=agentcore_gateway_role_name
        )
        print(f"recreating {agentcore_gateway_role_name}")
        agentcore_iam_role = iam_client.create_role(
            RoleName=agentcore_gateway_role_name,
            AssumeRolePolicyDocument=assume_role_policy_document_json
        )

    # Attach the AWSLambdaBasicExecutionRole policy
    print(f"attaching role policy {agentcore_gateway_role_name}")
    try:
        iam_client.put_role_policy(
            PolicyDocument=role_policy_document,
            PolicyName="AgentCorePolicy",
            RoleName=agentcore_gateway_role_name
        )
    except Exception as e:
        print(e)

    return agentcore_iam_role