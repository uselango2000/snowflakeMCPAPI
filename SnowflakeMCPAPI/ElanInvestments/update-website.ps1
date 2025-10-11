# Update Elan Investments Website on S3
# This script syncs changes to your existing S3 bucket

param(
    [Parameter(Mandatory=$true)]
    [string]$BucketName,
    
    [Parameter(Mandatory=$false)]
    [string]$ProfileName = "default"
)

# Color output functions
function Write-Success { Write-Host $args -ForegroundColor Green }
function Write-Info { Write-Host $args -ForegroundColor Cyan }
function Write-Error { Write-Host $args -ForegroundColor Red }

Write-Info "=========================================="
Write-Info "  Updating Elan Investments Website      "
Write-Info "=========================================="
Write-Host ""

# Check if bucket exists
Write-Info "Checking if bucket exists..."
$bucketCheck = aws s3api head-bucket --bucket $BucketName --profile $ProfileName 2>&1

if ($LASTEXITCODE -ne 0) {
    Write-Error "✗ Bucket '$BucketName' does not exist or you don't have access"
    Write-Info "Run the deploy-to-s3.ps1 script first to create the bucket"
    exit 1
}

Write-Success "✓ Bucket found"

# Sync files to S3
Write-Info "`nSyncing files to S3..."
aws s3 sync .\ s3://$BucketName/ --delete --exclude "*.json" --exclude "README.md" --exclude "*.ps1" --exclude "*.md" --cache-control "max-age=3600" --profile $ProfileName

if ($LASTEXITCODE -eq 0) {
    Write-Success "✓ Files synced successfully"
} else {
    Write-Error "✗ Failed to sync files"
    exit 1
}

# Set content types
Write-Info "Updating content types..."
aws s3 cp s3://$BucketName/index.html s3://$BucketName/index.html --content-type "text/html" --metadata-directive REPLACE --profile $ProfileName | Out-Null
aws s3 cp s3://$BucketName/styles.css s3://$BucketName/styles.css --content-type "text/css" --metadata-directive REPLACE --profile $ProfileName | Out-Null
aws s3 cp s3://$BucketName/script.js s3://$BucketName/script.js --content-type "application/javascript" --metadata-directive REPLACE --profile $ProfileName | Out-Null
Write-Success "✓ Content types updated"

# Get website URL
$region = aws s3api get-bucket-location --bucket $BucketName --profile $ProfileName --query "LocationConstraint" --output text 2>&1

if ($region -eq "None" -or $region -eq "null" -or [string]::IsNullOrEmpty($region)) {
    $region = "us-east-1"
    $websiteUrl = "http://$BucketName.s3-website-$region.amazonaws.com"
} else {
    $websiteUrl = "http://$BucketName.s3-website-$region.amazonaws.com"
}

Write-Host ""
Write-Success "=========================================="
Write-Success "  Update Complete! ✓"
Write-Success "=========================================="
Write-Host ""
Write-Info "Your website has been updated at:"
Write-Success $websiteUrl
Write-Host ""
