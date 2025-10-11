# AWS S3 Deployment Guide for Elan Investments

This guide will walk you through deploying your Elan Investments website to AWS S3.

## Prerequisites

### 1. Install AWS CLI

Download and install from: https://aws.amazon.com/cli/

Verify installation:
```powershell
aws --version
```

### 2. Configure AWS Credentials

You'll need an AWS account and IAM credentials with S3 permissions.

Run:
```powershell
aws configure
```

Enter your:
- **AWS Access Key ID**: (from IAM user)
- **AWS Secret Access Key**: (from IAM user)
- **Default region**: e.g., `us-east-1`
- **Default output format**: `json`

### 3. Required IAM Permissions

Your IAM user needs these permissions:
- `s3:CreateBucket`
- `s3:PutObject`
- `s3:PutObjectAcl`
- `s3:GetObject`
- `s3:DeleteObject`
- `s3:PutBucketWebsite`
- `s3:PutBucketPolicy`
- `s3:PutPublicAccessBlock`

## Deployment Scripts

### 1. deploy-to-s3.ps1
Creates a new S3 bucket and deploys your website.

**Usage:**
```powershell
.\deploy-to-s3.ps1 -BucketName "your-unique-bucket-name"
```

**With all options:**
```powershell
.\deploy-to-s3.ps1 -BucketName "elan-investments-site" -Region "us-west-2" -ProfileName "default"
```

**What it does:**
- ✓ Checks AWS CLI installation
- ✓ Verifies AWS credentials
- ✓ Creates S3 bucket
- ✓ Enables static website hosting
- ✓ Configures public access
- ✓ Sets bucket policy
- ✓ Uploads all website files
- ✓ Sets correct content types
- ✓ Displays website URL

### 2. update-website.ps1
Updates an existing S3 website with your latest changes.

**Usage:**
```powershell
.\update-website.ps1 -BucketName "your-bucket-name"
```

**What it does:**
- ✓ Syncs changed files to S3
- ✓ Removes deleted files (--delete flag)
- ✓ Updates content types
- ✓ Shows website URL

### 3. delete-s3-bucket.ps1
Removes the S3 bucket and all its contents.

**Usage:**
```powershell
.\delete-s3-bucket.ps1 -BucketName "your-bucket-name"
```

**Skip confirmation:**
```powershell
.\delete-s3-bucket.ps1 -BucketName "your-bucket-name" -Force
```

## Step-by-Step Deployment

### First Time Setup

1. **Open PowerShell in the project directory:**
   ```powershell
   cd C:\AI\SnowflakeMCPAPI\ElanInvestments
   ```

2. **Choose a unique bucket name:**
   - Must be globally unique
   - Use lowercase only
   - Example: `elan-investments-2025`

3. **Run the deployment script:**
   ```powershell
   .\deploy-to-s3.ps1 -BucketName "elan-investments-2025"
   ```

4. **Wait for completion:**
   - Script will show progress
   - Website URL will be displayed at the end

5. **Access your website:**
   - URL format: `http://[bucket-name].s3-website-[region].amazonaws.com`
   - Example: `http://elan-investments-2025.s3-website-us-east-1.amazonaws.com`

### Making Updates

1. **Edit your files** (index.html, styles.css, script.js)

2. **Sync changes to S3:**
   ```powershell
   .\update-website.ps1 -BucketName "elan-investments-2025"
   ```

3. **Refresh your browser** to see changes

## Troubleshooting

### Bucket Name Already Exists
**Error:** "BucketAlreadyExists"
**Solution:** Choose a different, unique bucket name

### Access Denied
**Error:** "Access Denied"
**Solution:** 
- Check AWS credentials: `aws sts get-caller-identity`
- Verify IAM permissions
- Reconfigure: `aws configure`

### Public Access Blocked
**Issue:** Website shows 403 Forbidden
**Solution:**
1. Go to AWS S3 Console
2. Select your bucket
3. Go to Permissions tab
4. Edit "Block public access" settings
5. Uncheck all boxes
6. Save changes
7. Re-run: `.\deploy-to-s3.ps1`

### Content Type Issues
**Issue:** CSS/JS not loading
**Solution:** Run update script to fix content types:
```powershell
.\update-website.ps1 -BucketName "your-bucket-name"
```

## Advanced Configuration

### Custom Domain Setup

1. **Register domain** (Route 53 or other registrar)

2. **Create CloudFront distribution:**
   - Origin: Your S3 bucket
   - Enable HTTPS

3. **Update DNS:**
   - Point domain to CloudFront distribution
   - Add CNAME or A record

### Enable HTTPS

Use AWS CloudFront:
1. Create CloudFront distribution
2. Select your S3 bucket as origin
3. Request SSL certificate (AWS Certificate Manager)
4. Update DNS to point to CloudFront

### Cost Optimization

- Enable S3 Intelligent-Tiering for storage
- Use CloudFront to reduce S3 data transfer costs
- Set lifecycle policies for old content

## Costs

### S3 Pricing (approximate)
- **Storage**: ~$0.023 per GB/month
- **Requests**: ~$0.005 per 1,000 GET requests
- **Data Transfer**: First 1 GB free, then ~$0.09/GB

### For a small website:
- Storage: < $0.01/month
- Requests: < $0.01/month (for low traffic)
- **Total**: Usually < $1/month for small sites

### CloudFront (optional)
- 1 TB data transfer: ~$85/month
- 10 million requests: ~$1/month

## Security Best Practices

1. **Use CloudFront** instead of direct S3 access
2. **Enable access logging**
3. **Use IAM roles** instead of hardcoded credentials
4. **Enable versioning** for backup/rollback
5. **Set up AWS WAF** for protection against attacks
6. **Use AWS Certificate Manager** for free SSL certificates

## Monitoring

### CloudWatch Metrics
Monitor in AWS Console:
- Bucket size
- Number of objects
- Request count
- Data transfer

### Access Logs
Enable S3 access logging:
```powershell
aws s3api put-bucket-logging --bucket your-bucket-name --bucket-logging-status file://logging.json
```

## Resources

- [AWS S3 Documentation](https://docs.aws.amazon.com/s3/)
- [Static Website Hosting](https://docs.aws.amazon.com/AmazonS3/latest/userguide/WebsiteHosting.html)
- [AWS CLI Reference](https://docs.aws.amazon.com/cli/latest/reference/s3/)
- [CloudFront Documentation](https://docs.aws.amazon.com/cloudfront/)

## Support

For issues or questions:
1. Check AWS service health dashboard
2. Review CloudWatch logs
3. Consult AWS documentation
4. Contact AWS support (if you have a support plan)
