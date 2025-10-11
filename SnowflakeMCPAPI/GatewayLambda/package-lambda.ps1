# PowerShell script to package Lambda function into ZIP file

param(
    [string]$OutputZipFile = "snowflakeMCPAPI.zip",
    [switch]$IncludeDependencies = $false
)

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Lambda Function Package Builder" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Create temporary directory for packaging
$tempDir = "lambda_package_temp"
if (Test-Path $tempDir) {
    Remove-Item -Path $tempDir -Recurse -Force
}
New-Item -ItemType Directory -Path $tempDir -Force | Out-Null

Write-Host "Copying Python files..." -ForegroundColor Yellow

# Copy main Lambda files
Copy-Item -Path "snowflakeMCPAPI.py" -Destination "$tempDir/lambda_function_code.py"
Copy-Item -Path "utils.py" -Destination "$tempDir/utils.py" -ErrorAction SilentlyContinue

# If IncludeDependencies flag is set, install packages into the package directory
if ($IncludeDependencies) {
    Write-Host "Installing dependencies into package..." -ForegroundColor Yellow
    pip install --target $tempDir `
        snowflake-connector-python `
        boto3 `
        python-dotenv `
        -q
    
    if ($LASTEXITCODE -ne 0) {
        Write-Host "ERROR: Failed to install dependencies!" -ForegroundColor Red
        Remove-Item -Path $tempDir -Recurse -Force
        exit 1
    }
    Write-Host "Dependencies installed successfully" -ForegroundColor Green
} else {
    Write-Host "Skipping dependencies (will use Lambda Layer)" -ForegroundColor Yellow
}

# Create ZIP file
Write-Host "Creating ZIP file: $OutputZipFile" -ForegroundColor Yellow

if (Test-Path $OutputZipFile) {
    Remove-Item -Path $OutputZipFile -Force
}

# Compress the contents
Compress-Archive -Path "$tempDir\*" -DestinationPath $OutputZipFile -Force

# Clean up temp directory
Remove-Item -Path $tempDir -Recurse -Force

# Get file size
$fileSize = (Get-Item $OutputZipFile).Length / 1MB
Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "Package created successfully!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host "File: $OutputZipFile" -ForegroundColor White
Write-Host "Size: $([math]::Round($fileSize, 2)) MB" -ForegroundColor White
Write-Host ""
Write-Host "You can now:" -ForegroundColor Yellow
Write-Host "1. Upload this ZIP to AWS Lambda directly via Console" -ForegroundColor White
Write-Host "2. Use it with the deploy.ps1 script for automated deployment" -ForegroundColor White
Write-Host "3. Deploy using AWS CLI:" -ForegroundColor White
Write-Host "   aws lambda update-function-code --function-name <name> --zip-file fileb://$OutputZipFile" -ForegroundColor Cyan
Write-Host ""
