param(
    [Parameter(Mandatory=$true)]
    [string]$BucketName,
    [string]$Region = 'us-east-1',
    [string]$ProfileName = 'default'
)

Write-Host '==========================================' -ForegroundColor Cyan
Write-Host '  Elan Investments S3 Deployment Script  ' -ForegroundColor Cyan
Write-Host '==========================================' -ForegroundColor Cyan
Write-Host ''

Write-Host 'Checking AWS CLI installation...' -ForegroundColor Cyan
$awsVersion = aws --version 2>&1
Write-Host ' AWS CLI is installed' -ForegroundColor Green

Write-Host 'Checking AWS credentials...' -ForegroundColor Cyan
aws sts get-caller-identity --profile $ProfileName | Out-Null
if ($LASTEXITCODE -eq 0) {
    Write-Host ' AWS credentials are configured' -ForegroundColor Green
} else {
    Write-Host ' AWS credentials not found!' -ForegroundColor Red
    exit 1
}

Write-Host ''
Write-Host 'Creating S3 bucket...' -ForegroundColor Cyan
$createResult = aws s3api create-bucket --bucket $BucketName --region $Region --profile $ProfileName 2>&1
if ($LASTEXITCODE -eq 0) {
    Write-Host ' Bucket created successfully' -ForegroundColor Green
} elseif ($createResult -like '*BucketAlreadyOwnedByYou*') {
    Write-Host ' Bucket already exists' -ForegroundColor Yellow
} else {
    Write-Host ' Error creating bucket' -ForegroundColor Red
    Write-Host $createResult
    exit 1
}

Write-Host 'Enabling static website hosting...' -ForegroundColor Cyan
aws s3 website s3://$BucketName/ --index-document index.html --error-document index.html --profile $ProfileName
Write-Host ' Static website hosting enabled' -ForegroundColor Green

Write-Host 'Configuring public access...' -ForegroundColor Cyan
aws s3api put-public-access-block --bucket $BucketName --public-access-block-configuration 'BlockPublicAcls=false,IgnorePublicAcls=false,BlockPublicPolicy=false,RestrictPublicBuckets=false' --profile $ProfileName

$policy = @'
{
    \"Version\": \"2012-10-17\",
    \"Statement\": [
        {
            \"Sid\": \"PublicReadGetObject\",
            \"Effect\": \"Allow\",
            \"Principal\": \"*\",
            \"Action\": \"s3:GetObject\",
            \"Resource\": \"arn:aws:s3:::BUCKETNAME/*\"
        }
    ]
}
'@ -replace 'BUCKETNAME', $BucketName

$policy | Out-File -FilePath '.\bucket-policy.json' -Encoding utf8

Write-Host 'Applying bucket policy...' -ForegroundColor Cyan
aws s3api put-bucket-policy --bucket $BucketName --policy file://bucket-policy.json --profile $ProfileName
Write-Host ' Bucket policy applied' -ForegroundColor Green

Write-Host ''
Write-Host 'Uploading website files...' -ForegroundColor Cyan
aws s3 sync .\ s3://$BucketName/ --exclude '*.json' --exclude 'README.md' --exclude '*.ps1' --exclude '*.md' --cache-control 'max-age=3600' --profile $ProfileName
Write-Host ' Website files uploaded' -ForegroundColor Green

Write-Host 'Setting content types...' -ForegroundColor Cyan
aws s3 cp s3://$BucketName/index.html s3://$BucketName/index.html --content-type 'text/html' --metadata-directive REPLACE --profile $ProfileName | Out-Null
aws s3 cp s3://$BucketName/styles.css s3://$BucketName/styles.css --content-type 'text/css' --metadata-directive REPLACE --profile $ProfileName | Out-Null
aws s3 cp s3://$BucketName/script.js s3://$BucketName/script.js --content-type 'application/javascript' --metadata-directive REPLACE --profile $ProfileName | Out-Null
Write-Host ' Content types configured' -ForegroundColor Green

$websiteUrl = 'http://' + $BucketName + '.s3-website-' + $Region + '.amazonaws.com'

Write-Host ''
Write-Host '==========================================' -ForegroundColor Green
Write-Host '  Deployment Complete!' -ForegroundColor Green
Write-Host '==========================================' -ForegroundColor Green
Write-Host ''
Write-Host 'Your website is now live at:' -ForegroundColor Cyan
Write-Host $websiteUrl -ForegroundColor Green
Write-Host ''

Remove-Item '.\bucket-policy.json' -Force -ErrorAction SilentlyContinue
