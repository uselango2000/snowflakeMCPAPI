# Deploy Elan Investments Website to AWS S3
# This script creates an S3 bucket and deploys the static website

param(
    [Parameter(Mandatory=$true)]
    [string]$BucketName,
    
    [Parameter(Mandatory=$false)]
    [string]$Region = "us-east-1",
    
    [Parameter(Mandatory=$false)]
    [string]$ProfileName = "default"
)

# Color output functions
function Write-Success { Write-Host $args -ForegroundColor Green }
function Write-Info { Write-Host $args -ForegroundColor Cyan }
function Write-Warning { Write-Host $args -ForegroundColor Yellow }
function Write-ErrorMsg { Write-Host $args -ForegroundColor Red }

Write-Info "=========================================="
Write-Info "  Elan Investments S3 Deployment Script  "
Write-Info "=========================================="
Write-Host ""

# Check if AWS CLI is installed
Write-Info "Checking AWS CLI installation..."
try {
    $awsVersion = aws --version 2>&1
    Write-Success "✓ AWS CLI is installed: $awsVersion"
} catch {
    Write-ErrorMsg "✗ AWS CLI is not installed!"
    Write-Info "Please install AWS CLI from: https://aws.amazon.com/cli/"
    exit 1
}

# Check if AWS credentials are configured
Write-Info "Checking AWS credentials..."
$identity = aws sts get-caller-identity --profile $ProfileName 2>&1
if ($LASTEXITCODE -eq 0) {
    Write-Success "✓ AWS credentials are configured"
} else {
    Write-ErrorMsg "✗ AWS credentials not found!"
    Write-Info "Run: aws configure --profile $ProfileName"
    exit 1
}

# Create S3 bucket
Write-Info "`nCreating S3 bucket: $BucketName..."
$createResult = aws s3api create-bucket --bucket $BucketName --region $Region --profile $ProfileName 2>&1

if ($LASTEXITCODE -eq 0) {
    Write-Success "✓ Bucket created successfully"
} elseif ($createResult -like "*BucketAlreadyOwnedByYou*") {
    Write-Warning "⚠ Bucket already exists and is owned by you"
} elseif ($createResult -like "*BucketAlreadyExists*") {
    Write-ErrorMsg "✗ Bucket name is already taken by another account"
    Write-Info "Please choose a different bucket name"
    exit 1
} else {
    Write-ErrorMsg "✗ Error creating bucket: $createResult"
    exit 1
}

# Enable static website hosting
Write-Info "Enabling static website hosting..."
aws s3 website s3://$BucketName/ --index-document index.html --error-document index.html --profile $ProfileName

if ($LASTEXITCODE -eq 0) {
    Write-Success "✓ Static website hosting enabled"
} else {
    Write-ErrorMsg "✗ Failed to enable static website hosting"
    exit 1
}

# Create bucket policy for public access
Write-Info "Creating bucket policy for public access..."
$policyJson = @"
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "PublicReadGetObject",
            "Effect": "Allow",
            "Principal": "*",
            "Action": "s3:GetObject",
            "Resource": "arn:aws:s3:::$BucketName/*"
        }
    ]
}
"@

$policyJson | Out-File -FilePath ".\bucket-policy.json" -Encoding utf8

# Disable Block Public Access settings
Write-Info "Configuring public access settings..."
aws s3api put-public-access-block --bucket $BucketName --public-access-block-configuration "BlockPublicAcls=false,IgnorePublicAcls=false,BlockPublicPolicy=false,RestrictPublicBuckets=false" --profile $ProfileName

if ($LASTEXITCODE -eq 0) {
    Write-Success "✓ Public access settings configured"
} else {
    Write-Warning "⚠ Warning: Could not modify public access settings"
}

# Apply bucket policy
Write-Info "Applying bucket policy..."
aws s3api put-bucket-policy --bucket $BucketName --policy file://bucket-policy.json --profile $ProfileName

if ($LASTEXITCODE -eq 0) {
    Write-Success "✓ Bucket policy applied"
} else {
    Write-ErrorMsg "✗ Failed to apply bucket policy"
    Write-Warning "You may need to manually enable public access in the AWS Console"
}

# Upload website files
Write-Info "`nUploading website files..."
aws s3 sync .\ s3://$BucketName/ --exclude "*.json" --exclude "README.md" --exclude "*.ps1" --exclude "*.md" --cache-control "max-age=3600" --profile $ProfileName

if ($LASTEXITCODE -eq 0) {
    Write-Success "✓ Website files uploaded successfully"
} else {
    Write-ErrorMsg "✗ Failed to upload website files"
    exit 1
}

# Set content types for specific files
Write-Info "Setting content types..."
aws s3 cp s3://$BucketName/index.html s3://$BucketName/index.html --content-type "text/html" --metadata-directive REPLACE --profile $ProfileName | Out-Null
aws s3 cp s3://$BucketName/styles.css s3://$BucketName/styles.css --content-type "text/css" --metadata-directive REPLACE --profile $ProfileName | Out-Null
aws s3 cp s3://$BucketName/script.js s3://$BucketName/script.js --content-type "application/javascript" --metadata-directive REPLACE --profile $ProfileName | Out-Null
Write-Success "✓ Content types configured"

# Get website URL
$websiteUrl = "http://$BucketName.s3-website-$Region.amazonaws.com"

Write-Host ""
Write-Success "=========================================="
Write-Success "  Deployment Complete! ✓"
Write-Success "=========================================="
Write-Host ""
Write-Info "Your website is now live at:"
Write-Success $websiteUrl
Write-Host ""
Write-Info "Bucket name: $BucketName"
Write-Info "Region: $Region"
Write-Host ""
Write-Info "To update your website, run:"
Write-Warning ".\update-website.ps1 -BucketName $BucketName -ProfileName $ProfileName"
Write-Host ""

# Clean up temporary policy file
if (Test-Path ".\bucket-policy.json") {
    Remove-Item ".\bucket-policy.json" -Force
}
