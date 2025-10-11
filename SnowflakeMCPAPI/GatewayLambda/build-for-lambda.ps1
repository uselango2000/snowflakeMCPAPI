# Build Lambda package using Docker for Linux compatibility
# This ensures dependencies are compiled for Amazon Linux

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Building Lambda Package for Linux" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check if Docker is running
Write-Host "Checking Docker..." -ForegroundColor Yellow
try {
    docker --version | Out-Null
    if ($LASTEXITCODE -ne 0) { throw "Docker not found" }
    Write-Host "✓ Docker is available" -ForegroundColor Green
} catch {
    Write-Host "✗ Docker is not installed or not running!" -ForegroundColor Red
    Write-Host "Please install Docker Desktop from: https://www.docker.com/products/docker-desktop/" -ForegroundColor Yellow
    exit 1
}

Write-Host ""

# Clean up old artifacts
Write-Host "Cleaning up old artifacts..." -ForegroundColor Yellow
if (Test-Path "lambda_package_temp") { Remove-Item -Recurse -Force "lambda_package_temp" }
if (Test-Path "snowflakeMCPAPI.zip") { Remove-Item "snowflakeMCPAPI.zip" }

# Create temp directory
New-Item -ItemType Directory -Path "lambda_package_temp" | Out-Null

Write-Host "Installing dependencies using Amazon Linux Docker image..." -ForegroundColor Yellow

# Use Amazon Linux 2023 image to install dependencies
docker run --rm -v "${PWD}:/workspace" -w /workspace public.ecr.aws/lambda/python:3.13 bash -c "pip install --target lambda_package_temp snowflake-connector-python boto3 -q; echo 'Dependencies installed'"

if ($LASTEXITCODE -ne 0) {
    Write-Host "✗ Failed to install dependencies!" -ForegroundColor Red
    exit 1
}

Write-Host "✓ Dependencies installed for Linux" -ForegroundColor Green

# Copy Python files
Write-Host "Copying application files..." -ForegroundColor Yellow
Copy-Item "snowflakeMCPAPI.py" "lambda_package_temp/lambda_function_code.py"
Copy-Item "utils.py" "lambda_package_temp/utils.py"

# Create ZIP
Write-Host "Creating ZIP file..." -ForegroundColor Yellow
Compress-Archive -Path "lambda_package_temp\*" -DestinationPath "snowflakeMCPAPI.zip"

# Get size
$size = [math]::Round((Get-Item "snowflakeMCPAPI.zip").Length / 1MB, 2)

# Clean up
Remove-Item -Recurse -Force "lambda_package_temp"

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "Package created successfully!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host "File: snowflakeMCPAPI.zip" -ForegroundColor White
Write-Host "Size: $size MB" -ForegroundColor White
Write-Host ""
Write-Host "Deploy with: python agentCoreGateway.py" -ForegroundColor Cyan
