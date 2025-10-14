"""
Agent Core Browser
A Python module for web browsing functionality with agent integration.
"""

import requests
from typing import Dict, List, Optional
from bs4 import BeautifulSoup
import json
from nova_act import NovaAct
from rich.console import Console
import argparse
import json
from boto3.session import Session
import os
from dotenv import load_dotenv
import boto3
from datetime import datetime
import glob

# Load environment variables from .env file
load_dotenv()


class AgentCoreBrowser:
    """
    A browser client for agent-based web interactions.
    Provides methods for fetching web content, parsing HTML, and extracting data.
    """
    
    def __init__(self, user_agent: Optional[str] = None):
        """
        Initialize the AgentCoreBrowser.
        
        Args:
            user_agent: Optional custom user agent string
        """
        self.session = requests.Session()
        self.user_agent = user_agent or "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        self.session.headers.update({
            'User-Agent': self.user_agent,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
        })
        
    def close(self):
        """Close the browser session."""
        self.session.close()


def upload_video_to_s3(video_path, bucket_name, region="us-east-1"):
    """Upload video to S3 and return the public URL."""
    try:
        s3_client = boto3.client('s3', region_name=region)
        
        # Create S3 key with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        video_filename = os.path.basename(video_path)
        s3_key = f"browser-automation-recordings/{timestamp}_{video_filename}"
        
        print(f"Uploading video to S3: s3://{bucket_name}/{s3_key}")
        s3_client.upload_file(video_path, bucket_name, s3_key)
        
        # Generate public URL
        s3_url = f"https://{bucket_name}.s3.{region}.amazonaws.com/{s3_key}"
        print(f"✓ Video uploaded successfully: {s3_url}")
        return s3_url
    except Exception as e:
        print(f"Error uploading video to S3: {e}")
        return None


def browser_with_nova_act(prompt, starting_page, use_api_key=False, nova_act_key=None, region="us-east-1", record_video=True, s3_bucket=None):
    result = None
    
    if use_api_key and nova_act_key:
        print(f"Initializing NovaAct with API key authentication in region: {region}")
        auth_params = {"nova_act_api_key": nova_act_key}
    else:
        print(f"Initializing NovaAct with AWS IAM (boto session) authentication in region: {region}")
        boto_session = Session(region_name=region)
        auth_params = {"boto_session": boto_session}
    
    try:
        with NovaAct(
            **auth_params,
            starting_page=starting_page,
            ignore_https_errors=True,
            headless=False,  # Set to True if you don't want to see the browser
            record_video=record_video,
            logs_directory="nova_act_logs"
        ) as nova_act:
            print("NovaAct initialized, executing prompt...")
            if record_video:
                print("📹 Video recording enabled")
            result = nova_act.act(prompt)
            print("NovaAct completed successfully!")
            
            # Upload video to S3 if recording was enabled and bucket specified
            if record_video and s3_bucket:
                print("\nSearching for recorded video...")
                video_files = glob.glob("nova_act_logs/**/*.webm", recursive=True)
                if video_files:
                    latest_video = max(video_files, key=os.path.getctime)
                    print(f"Found video: {latest_video}")
                    upload_video_to_s3(latest_video, s3_bucket, region)
                else:
                    print("⚠️ No video files found in nova_act_logs directory")
    except Exception as e:
        print(f"NovaAct error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        return result

def main():
    """Example usage of AgentCoreBrowser."""
    browser = AgentCoreBrowser()
    boto_session = Session()
    region = boto_session.region_name
    print("using region", region)
    
    parser = argparse.ArgumentParser()
    parser.add_argument("--prompt", required=True, help="Click Timesheet link and enter 7.25 hours in the Hours text and move the mouse to the Add Row.")
    parser.add_argument("--starting-page", required=True, help="http://elan-investments-2025.s3-website-us-east-1.amazonaws.com")
    parser.add_argument("--use-api-key", action="store_true", help="Use Nova Act API key instead of AWS IAM")
    parser.add_argument("--region", default=region, help="AWS region")
    parser.add_argument("--record-video", action="store_true", default=True, help="Record browser automation (default: True)")
    parser.add_argument("--s3-bucket", default="elan-investments-2025", help="S3 bucket for video upload (default: elan-investments-2025)")
    args = parser.parse_args()
    
    # Get Nova Act key from environment variable if using API key auth
    nova_act_key = None
    if args.use_api_key:
        nova_act_key = os.getenv("NOVA_ACT_API_KEY")
        if not nova_act_key:
            raise ValueError("NOVA_ACT_API_KEY not found in environment variables. Please set it in .env file")
    else:
        # When using boto session (IAM auth), we must unset NOVA_ACT_API_KEY 
        # because NovaAct will auto-detect it and throw an error
        if "NOVA_ACT_API_KEY" in os.environ:
            del os.environ["NOVA_ACT_API_KEY"]
    
    result = browser_with_nova_act(
        args.prompt, 
        args.starting_page, 
        use_api_key=args.use_api_key,
        nova_act_key=nova_act_key, 
        region=args.region,
        record_video=args.record_video,
        s3_bucket=args.s3_bucket
    )
    
    if result:
        print(f"\n[cyan] Response[/cyan] {result.response}")
        print(f"\n[bold green]Nova Act Result:[/bold green] {result}")
    else:
        print("\n[red]Error: NovaAct failed to execute. Check the error messages above.[/red]")

    browser.close()


if __name__ == "__main__":
    main()
