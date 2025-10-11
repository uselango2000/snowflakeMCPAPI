<#
Deploy script (PowerShell) - builds Docker image, pushes to ECR, creates IAM role and Lambda function.

Usage example (replace <account-id> or pass as parameter):
.\deploy-to-aws.ps1 -AccountId 123456789012 -Region us-east-1
#>

[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)][string]$AccountId,
    [string]$Region = 'us-east-1',
    [string]$RepoName = 'snowflake-lambda',
    [string]$ImageTag = 'latest',
    [string]$FunctionName = 'snowflake-lambda',
    [string]$RoleName = 'lambda-snowflake-role'
)

$ErrorActionPreference = 'Stop'

Write-Host "Starting deploy: repo=$RepoName region=$Region account=$AccountId"

# Validate AccountId looks like a 12-digit AWS account ID
if (-not $AccountId -or ($AccountId -notmatch '^[0-9]{12}$')) {
    throw "AccountId must be a 12-digit AWS account id. Provided: '$AccountId'"
}

# Build image (linux/amd64 to ensure Lambda compatibility)
Write-Host 'Building Docker image for linux/amd64...'
docker build --platform linux/amd64 -t "${RepoName}:${ImageTag}" .

# Create ECR repository (ignore error if exists)
Write-Host 'Creating ECR repository (if not exists)...'
# If repo exists, delete it first to ensure a clean recreate (this removes images in the repo)
try {
    $existing = aws ecr describe-repositories --repository-names $RepoName --region $Region 2>$null
    if ($LASTEXITCODE -eq 0) {
        Write-Host "ECR repository '$RepoName' exists - deleting and will recreate..."
        # Delete repository and all images (force)
        aws ecr delete-repository --repository-name $RepoName --region $Region --force | Out-Null
        Write-Host 'ECR repository deleted.'
    }
} catch {
    # describe-repositories may return non-zero when not found; ignore
}

try {
    aws ecr create-repository --repository-name $RepoName --region $Region | Out-Null
    Write-Host 'ECR repository created.'
} catch {
    Write-Host "Failed to create ECR repo: $($_.Exception.Message)"
    throw
}

$EcrUri = "$AccountId.dkr.ecr.$Region.amazonaws.com"

Write-Host 'Logging in to ECR...'
aws ecr get-login-password --region $Region | docker login --username AWS --password-stdin "$EcrUri"

Write-Host 'Tagging image...'
docker tag "${RepoName}:${ImageTag}" "$EcrUri/${RepoName}:${ImageTag}"

Write-Host 'Pushing image to ECR...'
docker push "$EcrUri/${RepoName}:${ImageTag}"

# Create IAM role for Lambda
Write-Host "Ensuring IAM role $RoleName exists..."
# If role exists, detach managed policies, delete inline policies, then delete role to recreate
try {
    $role = aws iam get-role --role-name $RoleName 2>$null
    if ($LASTEXITCODE -eq 0) {
        Write-Host "IAM role '$RoleName' exists - deleting and will recreate..."

        # Detach all attached managed policies
        $attached = aws iam list-attached-role-policies --role-name $RoleName | ConvertFrom-Json
        foreach ($p in $attached.AttachedPolicies) {
            Write-Host "Detaching managed policy: $($p.PolicyArn)"
            aws iam detach-role-policy --role-name $RoleName --policy-arn $p.PolicyArn | Out-Null
        }

        # Delete all inline policies
        $inlines = aws iam list-role-policies --role-name $RoleName | ConvertFrom-Json
        foreach ($pn in $inlines.PolicyNames) {
            Write-Host "Deleting inline policy: $pn"
            aws iam delete-role-policy --role-name $RoleName --policy-name $pn | Out-Null
        }

        # Delete the role (must remove instance profiles first if any)
        $profiles = aws iam list-instance-profiles-for-role --role-name $RoleName | ConvertFrom-Json
        foreach ($ip in $profiles.InstanceProfiles) {
            Write-Host "Removing role from instance profile: $($ip.InstanceProfileName)"
            aws iam remove-role-from-instance-profile --instance-profile-name $ip.InstanceProfileName --role-name $RoleName | Out-Null
            aws iam delete-instance-profile --instance-profile-name $ip.InstanceProfileName | Out-Null
        }

        aws iam delete-role --role-name $RoleName | Out-Null
        Write-Host 'IAM role deleted.'
    }
} catch {
    Write-Host 'IAM role not present or delete failed; continuing to (re)create.'
}

try {
    aws iam create-role --role-name $RoleName --assume-role-policy-document file://trust-lambda.json | Out-Null
    Write-Host 'Role created.'
} catch {
    Write-Host "Failed to create IAM role: $($_.Exception.Message)"
    throw
}

Write-Host 'Attaching AWSLambdaBasicExecutionRole managed policy...'
aws iam attach-role-policy --role-name $RoleName --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole

# Attach inline policy for Secrets Manager access scoped to this account/region
Write-Host 'Building inline SecretsManager access policy JSON...'
$secretsPolicyObj = @{
    Version = '2012-10-17'
    Statement = @(
        @{
            Effect = 'Allow'
            Action = @('secretsmanager:GetSecretValue')
            Resource = "arn:aws:secretsmanager:${Region}:${AccountId}:secret:*"
        }
    )
}

$secretsPolicyFile = Join-Path -Path $PSScriptRoot -ChildPath 'secrets-policy.json'
$secretsPolicyObj | ConvertTo-Json -Depth 5 | Out-String | Set-Content -Path $secretsPolicyFile -Encoding ASCII

# Delete any pre-existing inline policy to avoid conflicts
Write-Host 'Deleting existing inline policy (if any)...'
try {
    aws iam delete-role-policy --role-name $RoleName --policy-name SnowflakeSecretsAccess -ErrorAction Stop
    Write-Host 'Existing inline policy deleted.'
} catch {
    Write-Host 'No existing inline policy to delete or delete failed; continuing.'
}

Write-Host 'Putting inline SecretsManager access policy (from file)...'
aws iam put-role-policy --role-name $RoleName --policy-name SnowflakeSecretsAccess --policy-document file://$secretsPolicyFile

# (optional) remove the temp policy file
Remove-Item -Path $secretsPolicyFile -ErrorAction SilentlyContinue

# Wait briefly for IAM propagation (role/policy availability)
Write-Host 'Waiting briefly for IAM role/policy propagation...'
Start-Sleep -Seconds 8

# Create or update Lambda function using the image
$ImageUri = "$EcrUri/${RepoName}:${ImageTag}"
Write-Host "Creating or updating Lambda function $FunctionName with image $ImageUri"

# Build the role ARN explicitly (ensure AccountId interpolates correctly)
$RoleArn = "arn:aws:iam::${AccountId}:role/${RoleName}"
# If function exists, delete it first so it is recreated cleanly
try {
    $exists = aws lambda get-function --function-name $FunctionName --region $Region 2>$null
    if ($LASTEXITCODE -eq 0) {
        Write-Host "Lambda function '$FunctionName' exists - deleting and will recreate..."
        aws lambda delete-function --function-name $FunctionName --region $Region | Out-Null
        # wait a short moment for deletion to propagate
        Start-Sleep -Seconds 5
    }
} catch {
    # ignore not found
}

try {
    aws lambda create-function --function-name $FunctionName `
        --package-type Image `
        --code ImageUri=$ImageUri `
        --role $RoleArn `
        --region $Region `
        --timeout 30 `
        --memory-size 512 | Out-Null
    Write-Host 'Lambda function created.'
} catch {
    Write-Host "Failed to create Lambda function: $($_.Exception.Message)"
    throw
}

# Create AgentCore Gateway
Write-Host "Creating AgentCore Gateway..."
$GatewayName = "snowflake-gateway"
try {
    # Create or get Gateway IAM role first
    $GatewayRoleName = "bedrock-agentcore-gateway-role"
    $GatewayRoleArn = "arn:aws:iam::${AccountId}:role/${GatewayRoleName}"

    Write-Host "Creating/verifying Gateway IAM role..."
    try {
        $gatewayRole = aws iam get-role --role-name $GatewayRoleName 2>$null
        Write-Host "Found existing Gateway role: $GatewayRoleName"
    } catch {
        Write-Host "Creating new Gateway IAM role..."
        # Create trust policy for Gateway
        $gatewayTrustPolicy = @{
            Version = "2012-10-17"
            Statement = @(
                @{
                    Effect = "Allow"
                    Principal = @{
                        Service = "bedrock.amazonaws.com"
                    }
                    Action = "sts:AssumeRole"
                }
            )
        }
        $gatewayTrustPolicyJson = $gatewayTrustPolicy | ConvertTo-Json -Depth 10
        aws iam create-role --role-name $GatewayRoleName --assume-role-policy-document $gatewayTrustPolicyJson | Out-Null
        Write-Host "Gateway role created. Waiting for IAM propagation..."
        Start-Sleep -Seconds 10
    }

    # Attach or update Lambda invoke permissions
    Write-Host "Setting up Lambda invoke permissions..."
    $lambdaInvokePolicy = @{
        Version = "2012-10-17"
        Statement = @(
            @{
                Effect = "Allow"
                Action = "lambda:InvokeFunction"
                Resource = "arn:aws:lambda:${Region}:${AccountId}:function:${FunctionName}"
            }
        )
    }
    $lambdaInvokePolicyJson = $lambdaInvokePolicy | ConvertTo-Json -Depth 10
    aws iam put-role-policy --role-name $GatewayRoleName --policy-name "LambdaInvokeAccess" --policy-document $lambdaInvokePolicyJson | Out-Null
    Write-Host "Lambda invoke permissions added. Waiting for IAM propagation..."
    Start-Sleep -Seconds 10

    # Create the Gateway
    Write-Host "Creating AgentCore Gateway..."
    $gatewayResult = aws bedrock-agent create-agent-gateway `
        --name $GatewayName `
        --region $Region | ConvertFrom-Json

    if (-not $gatewayResult -or -not $gatewayResult.agentGatewayArn) {
        throw "Failed to get Gateway ARN from creation response"
    }

    $GatewayArn = $gatewayResult.agentGatewayArn
    Write-Host "Gateway created with ARN: $GatewayArn"
    
    # Extract Gateway ID from ARN and construct URL
    $GatewayId = $GatewayArn.Split('/')[-1]
    if (-not $GatewayId) {
        throw "Failed to extract Gateway ID from ARN: $GatewayArn"
    }

    # Add Lambda as Gateway target
    Write-Host "Adding Lambda as Gateway target..."
    $LambdaArn = "arn:aws:lambda:${Region}:${AccountId}:function:${FunctionName}"
    $GatewayUrl = "https://${GatewayId}.gateway.bedrock-agentcore.${Region}.amazonaws.com/mcp"

    Write-Host "Configuring Gateway target with URL: $GatewayUrl"
    aws bedrock-agent create-agent-gateway-target `
        --region $Region `
        --gateway-arn $GatewayArn `
        --gateway-url $GatewayUrl `
        --role-arn $GatewayRoleArn `
        --target-type lambda `
        --target-arn $LambdaArn `
        --outbound-authentication "GATEWAY_IAM_ROLE" | Out-Null

    Write-Host "Gateway target created successfully."

} catch {
    Write-Host "Failed to configure AgentCore Gateway: $($_.Exception.Message)"
    throw
}

Write-Host 'Deployment finished.'
Write-Host 'Invoke example: aws lambda invoke --function-name' $FunctionName '--payload' '{"sql":"SELECT current_version()"}' 'response.json --region' $Region
