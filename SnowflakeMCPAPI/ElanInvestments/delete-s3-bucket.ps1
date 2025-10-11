# Delete Elan Investments S3 Bucket
# This script removes the S3 bucket and all its contents

param(
    [Parameter(Mandatory=$true)]
    [string]$BucketName,
    
    [Parameter(Mandatory=$false)]
    [string]$ProfileName = "default",
    
    [Parameter(Mandatory=$false)]
    [switch]$Force
)

# Color output functions
function Write-Success { Write-Host $args -ForegroundColor Green }
function Write-Info { Write-Host $args -ForegroundColor Cyan }
function Write-Warning { Write-Host $args -ForegroundColor Yellow }
function Write-Error { Write-Host $args -ForegroundColor Red }

Write-Warning "=========================================="
Write-Warning "  WARNING: Bucket Deletion"
Write-Warning "=========================================="
Write-Host ""
Write-Warning "This will permanently delete the bucket: $BucketName"
Write-Warning "All files and configurations will be removed!"
Write-Host ""

if (-not $Force) {
    $confirmation = Read-Host "Are you sure you want to continue? (yes/no)"
    if ($confirmation -ne "yes") {
        Write-Info "Deletion cancelled"
        exit 0
    }
}

Write-Info "`nDeleting all objects from bucket..."
aws s3 rm s3://$BucketName/ --recursive --profile $ProfileName

if ($LASTEXITCODE -eq 0) {
    Write-Success "✓ Objects deleted"
} else {
    Write-Error "✗ Failed to delete objects"
    exit 1
}

Write-Info "Deleting bucket..."
aws s3api delete-bucket --bucket $BucketName --profile $ProfileName

if ($LASTEXITCODE -eq 0) {
    Write-Success "✓ Bucket deleted successfully"
    Write-Host ""
    Write-Success "Bucket '$BucketName' has been removed"
} else {
    Write-Error "✗ Failed to delete bucket"
    exit 1
}
