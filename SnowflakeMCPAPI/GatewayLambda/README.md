# GatewayLambda Folder

This folder contains the AWS Lambda function code and build scripts for the Snowflake MCP API.

## Files

### Lambda Source Code

- **snowflakeMCPAPI.py** - Lambda handler function
  - Receives SQL queries from the Gateway
  - Connects to Snowflake using credentials from AWS Secrets Manager
  - Executes queries and returns results
  - Returns format: `{"query": "...", "rows": [[...]]}`

### Build Scripts

- **build-for-lambda.ps1** - Builds Linux-compatible dependencies using Docker
  - Uses `python:3.13-slim` Docker image
  - Installs snowflake-connector-python and other dependencies
  - Creates Lambda-compatible package for Linux runtime
  
- **package-lambda.ps1** - Creates the Lambda deployment ZIP file
  - Packages Lambda code and dependencies
  - Creates `snowflakeMCPAPI.zip` ready for deployment

### Deployment Package

- **snowflakeMCPAPI.zip** - Lambda deployment package (26+ MB)
  - Contains Lambda handler code
  - Includes Linux-compatible Python dependencies
  - Ready to deploy to AWS Lambda

## Usage

### Build Lambda Package

```powershell
# Step 1: Build dependencies using Docker
.\build-for-lambda.ps1

# Step 2: Package into ZIP file
.\package-lambda.ps1
```

This creates `snowflakeMCPAPI.zip` which can be deployed to AWS Lambda.

### Deploy Lambda

The Gateway deployment script (`../Gateway/agentCoreGateway.py`) automatically:
1. Reads the ZIP file from this folder
2. Creates or updates the Lambda function
3. Configures timeout (30s) and memory (512MB)
4. Attaches IAM role for Secrets Manager access

## Lambda Configuration

- **Runtime**: Python 3.13
- **Handler**: `lambda_function_code.lambda_handler`
- **Timeout**: 30 seconds
- **Memory**: 512 MB
- **IAM Role**: `lambda-snowflake-role`
- **Environment**: AWS Secrets Manager for Snowflake credentials

## Snowflake Credentials

Lambda expects credentials in AWS Secrets Manager:
- **Secret Name**: `snowflake/demo_user`
- **Required Fields**:
  - `user` - Snowflake username
  - `password` - Snowflake password
  - `account` - Snowflake account identifier
  - `warehouse` - Snowflake warehouse name
  - `database` - Snowflake database name
  - `schema` - Snowflake schema name

## Lambda Handler

```python
def lambda_handler(event, context):
    """
    Handles SQL query execution on Snowflake
    
    Input: {"sql": "SELECT ..."}
    Output: {"query": "...", "rows": [[...]]}
    """
```

## Dependencies

- snowflake-connector-python
- boto3
- botocore

All dependencies are included in the ZIP file after running `build-for-lambda.ps1`.

## Rebuild Package

If you modify `snowflakeMCPAPI.py` or need to update dependencies:

```powershell
# Rebuild everything
.\build-for-lambda.ps1
.\package-lambda.ps1

# Redeploy from Gateway folder
cd ..\Gateway
python agentCoreGateway.py
```

## Architecture Flow

```
Client Request
    ↓
Bedrock Gateway (MCP Protocol)
    ↓
Lambda Function (this folder)
    ↓ 
AWS Secrets Manager (credentials)
    ↓
Snowflake Database
```
