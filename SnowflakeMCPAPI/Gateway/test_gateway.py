"""
Test script to invoke Snowflake MCP Gateway
This script calls the Bedrock AgentCore Gateway which invokes the Lambda
"""

import boto3
import json
from dotenv import load_dotenv
import os

load_dotenv()

import boto3
import json
import os
import requests
from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest


def test_gateway():
    """Test the Snowflake MCP Gateway"""
    
    # Configuration
    gateway_id = "snowflakemcpgateway-3krg53ika3"
    region = os.environ.get('AWS_DEFAULT_REGION', 'us-east-1')
    gateway_url = f"https://{gateway_id}.gateway.bedrock-agentcore.{region}.amazonaws.com/mcp"
    
    print("=" * 70)
    print("Testing Snowflake MCP Gateway")
    print("=" * 70)
    print(f"Gateway ID: {gateway_id}")
    print(f"Gateway URL: {gateway_url}")
    print(f"Region: {region}")
    print(f"Tool: execute_snowflake_query")
    print("")
    
    # Get AWS credentials for signing
    session = boto3.Session()
    credentials = session.get_credentials()
    print("✓ Retrieved AWS credentials")
    
    # First, initialize the MCP session
    print("\n" + "=" * 70)
    print("Step 1: Initialize MCP Session")
    print("=" * 70)
    
    init_request = {
        "jsonrpc": "2.0",
        "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {
                "name": "test-client",
                "version": "1.0.0"
            }
        },
        "id": 0
    }
    
    try:
        request = AWSRequest(
            method='POST',
            url=gateway_url,
            data=json.dumps(init_request),
            headers={'Content-Type': 'application/json'}
        )
        SigV4Auth(credentials, 'bedrock-agentcore', region).add_auth(request)
        
        response = requests.post(gateway_url, headers=dict(request.headers), data=request.body)
        
        if response.status_code == 200:
            init_result = response.json()
            print("✓ MCP session initialized successfully!")
            print(f"Response: {json.dumps(init_result, indent=2)}")
        else:
            print(f"✗ Initialize failed: {response.status_code}")
            print(f"Response: {response.text}")
            return
    except Exception as e:
        print(f"✗ Initialize error: {e}")
        return
    
    # List available tools
    print("\n" + "=" * 70)
    print("Step 2: List Available Tools")
    print("=" * 70)
    
    list_tools_request = {
        "jsonrpc": "2.0",
        "method": "tools/list",
        "params": {},
        "id": "list-tools"
    }
    
    try:
        request = AWSRequest(
            method='POST',
            url=gateway_url,
            data=json.dumps(list_tools_request),
            headers={'Content-Type': 'application/json'}
        )
        SigV4Auth(credentials, 'bedrock-agentcore', region).add_auth(request)
        
        response = requests.post(gateway_url, headers=dict(request.headers), data=request.body)
        
        if response.status_code == 200:
            tools_result = response.json()
            print("✓ Tools listed successfully!")
            print(f"Response: {json.dumps(tools_result, indent=2)}")
        else:
            print(f"✗ List tools failed: {response.status_code}")
            print(f"Response: {response.text}")
    except Exception as e:
        print(f"✗ List tools error: {e}")
    
    # Test queries
    test_queries = [
        {
            "name": "Get Snowflake Version",
            "sql": "SELECT current_version()"
        },
        {
            "name": "Get Current User",
            "sql": "SELECT current_user()"
        },
        {
            "name": "Get Current Database",
            "sql": "SELECT current_database()"
        }
    ]
    
    for i, test in enumerate(test_queries, 1):
        print(f"\n{'=' * 70}")
        print(f"Test {i}: {test['name']}")
        print(f"{'=' * 70}")
        print(f"SQL Query: {test['sql']}")
        print("")
        
        try:
            # Prepare MCP request payload
            # NOTE: Gateway prefixes tool name with target name
            mcp_request = {
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {
                    "name": "SnowflakeLambdaTarget___execute_snowflake_query",
                    "arguments": {
                        "sql": test['sql']
                    }
                },
                "id": i
            }
            
            # Create AWS signed request
            print("Creating AWS SigV4 signed request...")
            request = AWSRequest(
                method='POST',
                url=gateway_url,
                data=json.dumps(mcp_request),
                headers={
                    'Content-Type': 'application/json'
                }
            )
            
            # Sign the request
            SigV4Auth(credentials, 'bedrock-agentcore', region).add_auth(request)
            
            # Send the request
            print("Invoking gateway...")
            response = requests.post(
                gateway_url,
                headers=dict(request.headers),
                data=request.body
            )
            
            # Check response status
            if response.status_code == 200:
                result = response.json()
                print("✓ Gateway invoked successfully!")
                print(f"\nResponse:")
                print(json.dumps(result, indent=2))
            else:
                print(f"✗ Gateway returned error: {response.status_code}")
                print(f"Response: {response.text}")
            
        except Exception as e:
            error_str = str(e)
            print(f"✗ Error invoking gateway: {e}")
            
            if "AccessDenied" in error_str or "403" in error_str:
                print("\nTroubleshooting:")
                print("- Check that your AWS credentials have permission to invoke the gateway")
                print("- Verify the gateway uses AWS_IAM authentication")
            elif "ResourceNotFound" in error_str or "404" in error_str:
                print("\nTroubleshooting:")
                print("- Verify the gateway ID is correct")
                print("- Check that the gateway exists in the region")
            elif "ValidationException" in error_str:
                print("\nTroubleshooting:")
                print("- Check the tool name: execute_snowflake_query")
                print("- Verify the input schema matches")
    
    print(f"\n{'=' * 70}")
    print("Test Complete!")
    print(f"{'=' * 70}")


def test_direct_lambda():
    """Test the Lambda function directly (bypass gateway)"""
    
    print("\n" + "=" * 70)
    print("Testing Lambda Function Directly (Bypass Gateway)")
    print("=" * 70)
    
    lambda_client = boto3.client('lambda', region_name='us-east-1')
    function_name = 'snowflakeMCPAPILambda'
    
    test_payload = {
        'sql': 'SELECT current_version()'
    }
    
    print(f"Function: {function_name}")
    print(f"Payload: {json.dumps(test_payload)}")
    print("")
    
    try:
        print("Invoking Lambda...")
        response = lambda_client.invoke(
            FunctionName=function_name,
            InvocationType='RequestResponse',
            Payload=json.dumps(test_payload)
        )
        
        result = json.loads(response['Payload'].read())
        
        print("✓ Lambda invoked successfully!")
        print(f"\nResponse:")
        print(json.dumps(result, indent=2))
        
    except Exception as e:
        print(f"✗ Error invoking Lambda: {e}")


if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("SNOWFLAKE MCP GATEWAY TEST SUITE")
    print("=" * 70)
    print("")
    
    # Test 1: Direct Lambda (to verify Lambda works)
    test_direct_lambda()
    
    # Test 2: Gateway (to verify end-to-end flow)
    test_gateway()
