# Elan Investments Website

A professional static website for Elan Investments, featuring a modern design with responsive layout.

## Features

- **Responsive Design**: Works seamlessly on desktop, tablet, and mobile devices
- **Smooth Animations**: Fade-in effects and smooth scrolling for better user experience
- **Modern UI**: Clean and professional design with a blue and gold color scheme
- **Mobile Navigation**: Hamburger menu for mobile devices
- **Contact Form**: Interactive contact form for client inquiries
- **Multiple Sections**: 
  - Hero section with call-to-action
  - About section with key features
  - Services grid showcasing offerings
  - Portfolio/Investment approach section
  - Contact information and form
  - Professional footer with disclaimer

## File Structure

```
ElanInvestments/
├── index.html      # Main HTML file
├── styles.css      # All styling and responsive design
├── script.js       # Interactive functionality and animations
└── README.md       # This file
```

## How to Use

### Local Development
Simply open `index.html` in a web browser to view the site locally.

### Deploy to AWS S3

#### Prerequisites
1. Install [AWS CLI](https://aws.amazon.com/cli/)
2. Configure AWS credentials:
   ```powershell
   aws configure
   ```
   You'll need:
   - AWS Access Key ID
   - AWS Secret Access Key
   - Default region (e.g., us-east-1)

#### Deployment Steps

1. **Initial Deployment** - Deploy your website to a new S3 bucket:
   ```powershell
   .\deploy-to-s3.ps1 -BucketName "elan-investments-website"
   ```
   
   Optional parameters:
   ```powershell
   .\deploy-to-s3.ps1 -BucketName "elan-investments-website" -Region "us-west-2" -ProfileName "myprofile"
   ```

2. **Update Website** - Sync changes after editing files:
   ```powershell
   .\update-website.ps1 -BucketName "elan-investments-website"
   ```

3. **Delete Bucket** - Remove the S3 bucket and all contents:
   ```powershell
   .\delete-s3-bucket.ps1 -BucketName "elan-investments-website"
   ```

#### Important Notes
- Bucket names must be globally unique across all AWS accounts
- Use lowercase letters, numbers, and hyphens only
- The website will be accessible at: `http://[bucket-name].s3-website-[region].amazonaws.com`
- For production use, consider adding CloudFront CDN and a custom domain

### Alternative Deployment Options
- GitHub Pages
- Netlify
- Vercel
- Azure Static Web Apps

## Customization

### Colors
Edit the CSS variables in `styles.css`:
```css
:root {
    --primary-color: #1a5490;
    --secondary-color: #2c7bc4;
    --accent-color: #e8b923;
}
```

### Content
- Update text content in `index.html`
- Replace contact information with actual details
- Add real company logo if available

### Images
To add images:
1. Create an `images` folder
2. Add your images
3. Update the HTML to reference them

## Browser Support

- Chrome (latest)
- Firefox (latest)
- Safari (latest)
- Edge (latest)
- Mobile browsers

## License

© 2025 Elan Investments. All rights reserved.
