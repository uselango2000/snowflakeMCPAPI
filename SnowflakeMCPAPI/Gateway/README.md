# Gateway Folder

This folder contains the AWS Bedrock AgentCore Gateway management code for the Snowflake MCP API.

## Files

### Core Files

- **agentCoreGateway.py** - Main deployment orchestration script
  - Creates IAM roles for Lambda and Gateway
  - Deploys Lambda function
  - Creates Bedrock AgentCore Gateway
  - Creates Gateway Target with tool schema
  - Run: `python agentCoreGateway.py`

- **utils.py** - Helper functions
  - `create_gateway_lambda()` - Deploys Lambda function
  - `create_agentcore_gateway_role()` - Creates Gateway IAM role

- **test_gateway.py** - End-to-end test suite
  - Tests Lambda function directly
  - Tests MCP Gateway with AWS SigV4 authentication
  - Executes sample Snowflake queries
  - Run: `python test_gateway.py`

## Usage

### Deploy the Gateway

```bash
cd Gateway
python agentCoreGateway.py
```

This will:
1. Create IAM roles
2. Deploy Lambda function (from `../snowflakeMCPAPI.zip`)
3. Create Bedrock AgentCore Gateway
4. Create Gateway Target with tool schema

### Test the Gateway

```bash
cd Gateway
python test_gateway.py
```

This will:
1. Test Lambda function directly
2. Initialize MCP session with Gateway
3. List available tools
4. Execute 3 sample Snowflake queries through the Gateway

## Dependencies

- boto3
- python-dotenv
- requests
- botocore

All dependencies are managed in the parent folder's `requirements.txt`.

## Environment Variables

The scripts automatically load environment variables from `../.env`:
- AWS_ACCESS_KEY_ID
- AWS_SECRET_ACCESS_KEY
- AWS_DEFAULT_REGION

## Gateway Architecture

```
Client (with AWS SigV4 auth)
    ↓
Bedrock AgentCore Gateway (MCP Protocol)
    ↓
Gateway Target (Tool Schema)
    ↓
Lambda Function (snowflakeMCPAPILambda)
    ↓
Snowflake Database
```

## Tool Name

The Gateway automatically prefixes tool names with the target name:
- Defined tool: `execute_snowflake_query`
- Actual tool name: `SnowflakeLambdaTarget___execute_snowflake_query`

## Output

After successful deployment:
- **Gateway URL**: `https://{gateway-id}.gateway.bedrock-agentcore.{region}.amazonaws.com/mcp`
- **Lambda ARN**: `arn:aws:lambda:{region}:{account}:function:snowflakeMCPAPILambda`
- **Authentication**: AWS_IAM (SigV4)
