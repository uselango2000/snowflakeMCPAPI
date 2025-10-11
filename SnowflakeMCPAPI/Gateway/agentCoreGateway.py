"""
AgentCore Gateway
A module for managing AWS IAM roles and policies for AgentCore Gateway
"""

import boto3
import json
from typing import Dict, Any, Optional
from dotenv import load_dotenv
import os
import utils

# Load environment variables from .env file (one level up from Gateway folder)
env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env')
load_dotenv(dotenv_path=env_path)

# Now you can access them
aws_access_key = os.environ.get('AWS_ACCESS_KEY_ID')
aws_secret_key = os.environ.get('AWS_SECRET_ACCESS_KEY')
aws_region = os.environ.get('AWS_DEFAULT_REGION')

class AgentCoreGateway:
    def __init__(self, region: str = "us-east-1"):
        """        Initialize AgentCore Gateway manager
        
        Args:
            region: AWS region (default: us-east-1)
        """
        self.iam_client = boto3.client('iam', region_name=region)
        self.sts_client = boto3.client('sts', region_name=region)
        self.region = region
        self.account_id = self.sts_client.get_caller_identity()["Account"]
    
    def create_gateway_role(self, gateway_name: str) -> Dict[str, Any]:
        """
        Create an IAM role for AgentCore Gateway
        
        Args:
            gateway_name: Name of the gateway
            
        Returns:
            Dictionary containing role information
        """
        role_name = f'agentcore-{gateway_name}-role'
        
        # Trust policy for Lambda
        trust_policy = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Principal": {
                        "Service": "lambda.amazonaws.com"
                    },
                    "Action": "sts:AssumeRole"
                }
            ]
        }
        
        try:
            response = self.iam_client.create_role(
                RoleName=role_name,
                AssumeRolePolicyDocument=json.dumps(trust_policy),
                Description=f"IAM role for AgentCore Gateway: {gateway_name}"
            )
            
            # Attach basic Lambda execution policy
            self.iam_client.attach_role_policy(
                RoleName=role_name,
                PolicyArn='arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole'
            )
            
            return response
        except self.iam_client.exceptions.EntityAlreadyExistsException:
            print(f"Role {role_name} already exists. Retrieving existing role...")
            return self.iam_client.get_role(RoleName=role_name)
    
    def attach_policy(self, role_name: str, policy_arn: str) -> None:
        """
        Attach a policy to a role
        
        Args:
            role_name: Name of the IAM role
            policy_arn: ARN of the policy to attach
        """
        self.iam_client.attach_role_policy(
            RoleName=role_name,
            PolicyArn=policy_arn
        )
        print(f"Attached policy {policy_arn} to role {role_name}")
    
    def create_custom_policy(self, policy_name: str, policy_document: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a custom IAM policy
        
        Args:
            policy_name: Name of the policy
            policy_document: Policy document as a dictionary
            
        Returns:
            Dictionary containing policy information
        """
        try:
            response = self.iam_client.create_policy(
                PolicyName=policy_name,
                PolicyDocument=json.dumps(policy_document),
                Description=f"Custom policy for {policy_name}"
            )
            return response
        except self.iam_client.exceptions.EntityAlreadyExistsException:
            print(f"Policy {policy_name} already exists.")
            policy_arn = f"arn:aws:iam::{self.account_id}:policy/{policy_name}"
            return self.iam_client.get_policy(PolicyArn=policy_arn)
    
    def create_gateway(self, gateway_name: str, lambda_arn: str, auth_type: str = "AWS_IAM") -> Dict[str, Any]:
        """
        Create a Bedrock AgentCore Gateway
        
        Args:
            gateway_name: Name of the gateway
            lambda_arn: ARN of the Lambda function to integrate
            auth_type: Authentication type (AWS_IAM or CUSTOM_JWT)
            
        Returns:
            Dictionary containing gateway information
        """
        print(f"\nCreating Bedrock AgentCore Gateway: {gateway_name}")
        print(f"Authentication Type: {auth_type}")
        
        # Create AgentCore Gateway IAM role
        agentcore_gateway_iam_role = utils.create_agentcore_gateway_role(gateway_name)
        
        # Initialize gateway client
        gateway_client = boto3.client(
            'bedrock-agentcore-control', 
            region_name=self.region
        )
        
        try:
            create_response = gateway_client.create_gateway(
                name=gateway_name,
                roleArn=agentcore_gateway_iam_role['Role']['Arn'],
                protocolType='MCP',
                authorizerType=auth_type,
                description=f'AgentCore Gateway for {gateway_name} with {auth_type} authentication'
            )
            
            print(f"\n✓ Gateway created successfully!")
            print(f"  Gateway ID: {create_response['gatewayId']}")
            print(f"  Gateway URL: {create_response['gatewayUrl']}")
            print(f"  Authorizer Type: {auth_type}")
            
            if auth_type == "IAM":
                print(f"  Use AWS SigV4 signing to authenticate requests")
            
            return create_response
            
        except Exception as e:
            error_msg = str(e)
            if "already exists" in error_msg.lower():
                print(f"\n✓ Gateway '{gateway_name}' already exists. Retrieving...")
                try:
                    # List gateways to find existing one
                    list_response = gateway_client.list_gateways()
                    for gw in list_response.get('gateways', []):
                        if gw['name'] == gateway_name:
                            print(f"  Gateway ID: {gw['gatewayId']}")
                            print(f"  Gateway URL: {gw['gatewayUrl']}")
                            return gw
                    print(f"  Could not find gateway details")
                except Exception as list_err:
                    print(f"  Error retrieving gateway: {list_err}")
            else:
                print(f"✗ Error creating gateway: {e}")
                print("  Check if Bedrock AgentCore is enabled in your AWS account")
            return None
    
    def create_gateway_target(self, gateway_id: str, lambda_arn: str, target_name: str = "SnowflakeLambdaTarget") -> Dict[str, Any]:
        """
        Create a gateway target to connect Lambda function to the gateway
        
        Args:
            gateway_id: The ID of the gateway
            lambda_arn: ARN of the Lambda function
            target_name: Name for the gateway target
            
        Returns:
            Dictionary containing target information
        """
        print(f"\nCreating Gateway Target: {target_name}")
        print(f"Lambda ARN: {lambda_arn}")
        
        # Initialize gateway client
        gateway_client = boto3.client(
            'bedrock-agentcore-control', 
            region_name=self.region
        )
        
        # Configure Lambda target with Snowflake SQL tool
        # Default payload: {'sql': 'SELECT current_version()'}
        lambda_target_config = {
            "mcp": {
                "lambda": {
                    "lambdaArn": lambda_arn,
                    "toolSchema": {
                        "inlinePayload": [
                            {
                                "name": "execute_snowflake_query",
                                "description": "Execute a SQL query on Snowflake database. Default query: SELECT current_version()",
                                "inputSchema": {
                                    "type": "object",
                                    "properties": {
                                        "sql": {
                                            "type": "string",
                                            "description": "SQL query to execute on Snowflake"
                                        }
                                    },
                                    "required": ["sql"]
                                }
                            }
                        ]
                    }
                }
            }
        }
        
        # Credential configuration using Gateway IAM Role
        credential_config = [
            {
                "credentialProviderType": "GATEWAY_IAM_ROLE"
            }
        ]
        
        try:
            response = gateway_client.create_gateway_target(
                gatewayIdentifier=gateway_id,
                name=target_name,
                description='Snowflake Lambda Target - Default payload: {"sql": "SELECT current_version()"}',
                targetConfiguration=lambda_target_config,
                credentialProviderConfigurations=credential_config
            )
            
            print(f"\n✓ Gateway Target created successfully!")
            print(f"  Target Name: {target_name}")
            print(f"  Target ID: {response.get('targetId', 'N/A')}")
            print(f"  Tool: execute_snowflake_query")
            print(f"  Default Payload: {{'sql': 'SELECT current_version()'}}")
            
            return response
            
        except Exception as e:
            error_msg = str(e)
            if "already exists" in error_msg.lower():
                print(f"\n✓ Target '{target_name}' already exists!")
            else:
                print(f"\n✗ Error creating gateway target: {e}")
            return None


def main():
    """Main entry point for AgentCore Gateway"""
    gateway = AgentCoreGateway()
    
    # Step 1: Create Lambda IAM role
    print("=" * 60)
    print("STEP 1: Creating Lambda IAM Role")
    print("=" * 60)
    role = gateway.create_gateway_role("gateway")
    print(f"✓ Created/Retrieved role: {role['Role']['Arn']}")
    
    # Step 2: Deploy Lambda function
    print("\n" + "=" * 60)
    print("STEP 2: Deploying Lambda Function")
    print("=" * 60)
    # Get the path to the ZIP file (in GatewayLambda folder, sibling to Gateway)
    script_dir = os.path.dirname(os.path.abspath(__file__))
    parent_dir = os.path.dirname(script_dir)
    zip_path = os.path.join(parent_dir, "GatewayLambda", "snowflakeMCPAPI.zip")
    lambda_resp = utils.create_gateway_lambda(zip_path)

    if lambda_resp is not None:
        if lambda_resp['exit_code'] == 0:
            lambda_arn = lambda_resp['lambda_function_arn']
            print(f"✓ Lambda function created with ARN: {lambda_arn}")
            
            # Step 3: Create Bedrock AgentCore Gateway
            print("\n" + "=" * 60)
            print("STEP 3: Creating Bedrock AgentCore Gateway")
            print("=" * 60)
            gateway_response = gateway.create_gateway(
                gateway_name='SnowflakeMCPGateway',
                lambda_arn=lambda_arn,
                auth_type='AWS_IAM'
            )
            
            # Use existing gateway ID or get from response
            if gateway_response:
                gateway_id = gateway_response.get('gatewayId', 'snowflakemcpgateway-3krg53ika3')
            else:
                # If gateway already exists, use known gateway ID
                gateway_id = 'snowflakemcpgateway-3krg53ika3'
                print(f"\nUsing existing gateway ID: {gateway_id}")
            
            # Step 4: Create Gateway Target
            print("\n" + "=" * 60)
            print("STEP 4: Creating Gateway Target")
            print("=" * 60)
            target_response = gateway.create_gateway_target(
                gateway_id=gateway_id,
                lambda_arn=lambda_arn,
                target_name='SnowflakeLambdaTarget'
            )
            
            # Summary
            print("\n" + "=" * 60)
            print("DEPLOYMENT SUMMARY")
            print("=" * 60)
            print(f"✓ Lambda Function: {lambda_arn}")
            print(f"✓ Gateway ID: {gateway_id}")
            if gateway_response and 'gatewayUrl' in gateway_response:
                print(f"✓ Gateway URL: {gateway_response['gatewayUrl']}")
            else:
                print(f"✓ Gateway URL: https://{gateway_id}.gateway.bedrock-agentcore.us-east-1.amazonaws.com/mcp")
            print(f"✓ Authentication: AWS_IAM (SigV4)")
            if target_response:
                print(f"✓ Gateway Target: SnowflakeLambdaTarget")
                print(f"  Tool: execute_snowflake_query")
                print(f"  Default Payload: {{'sql': 'SELECT current_version()'}}")
            print("=" * 60)
        else:
            print(f"✗ Lambda function creation failed: {lambda_resp['lambda_function_arn']}")


if __name__ == "__main__":
    main()
