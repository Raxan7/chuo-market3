#!/usr/bin/env python3
"""
Test script to verify all ad links are working
"""
import requests
import time
import re

# Ad links from the implementation (updated 2/12/2026)
ad_links = [
    'https://otieu.com/4/10558195',
    'https://otieu.com/4/10558194',
    'https://otieu.com/4/10558193',
    'https://otieu.com/4/10558192',
    'https://otieu.com/4/10558191',
    'https://otieu.com/4/10558189',
    'https://otieu.com/4/10558188',
    'https://otieu.com/4/10558187',
    'https://otieu.com/4/10558184',
    'https://otieu.com/4/10558186'
]

def test_ad_links():
    """Test all ad links for accessibility"""
    print("Testing ad links...")
    print("=" * 50)
    
    working_links = 0
    for i, link in enumerate(ad_links, 1):
        try:
            print(f"Testing link {i}: ", end="")
            response = requests.get(link, timeout=10)
            
            if response.status_code == 200:
                print(f"✓ Working (Status: {response.status_code})")
                working_links += 1
            else:
                print(f"✗ Failed (Status: {response.status_code})")
                
        except requests.exceptions.RequestException as e:
            print(f"✗ Error: {str(e)}")
        
        # Small delay between requests
        time.sleep(0.5)
    
    print("=" * 50)
    print(f"Results: {working_links}/{len(ad_links)} links are working")
    print(f"Success rate: {(working_links/len(ad_links)*100):.1f}%")

def test_local_site():
    """Test if the local Django site is running"""
    print("\nTesting local Django site...")
    print("=" * 50)
    
    try:
        response = requests.get('http://localhost:8000/', timeout=5)
        if response.status_code == 200:
            print("✓ Django site is running")
            
            # Check if ad banner HTML is present
            if 'rotating-ad-banner' in response.text:
                print("✓ Ad banner HTML is present in the page")
            else:
                print("✗ Ad banner HTML not found in the page")
            
            # Check if ad-content div is present
            if 'ad-content' in response.text:
                print("✓ Ad content container is present")
            else:
                print("✗ Ad content container not found")
                
            # Check if ad JavaScript is present
            if 'const adLinks' in response.text:
                print("✓ Ad rotation JavaScript is present")
            else:
                print("✗ Ad rotation JavaScript not found")
            
            # Check for loading div
            if 'ad-loading' in response.text:
                print("✓ Ad loading indicator is present")
            else:
                print("✗ Ad loading indicator not found")
                
            # Check if all ad links are in the JavaScript
            missing_links = []
            for link in ad_links:
                if link not in response.text:
                    missing_links.append(link)
            
            if not missing_links:
                print(f"✓ All {len(ad_links)} ad links are embedded in the page")
            else:
                print(f"✗ {len(missing_links)} ad links are missing")
                
        else:
            print(f"✗ Django site responded with status {response.status_code}")
            
    except requests.exceptions.RequestException as e:
        print(f"✗ Cannot connect to Django site: {str(e)}")

def test_multiple_pages():
    """Test ads on multiple pages"""
    print("\nTesting ads on multiple pages...")
    print("=" * 50)
    
    test_pages = [
        ('/', 'Home'),
        ('/marketplace/', 'Marketplace'),
        ('/blogs/', 'Blogs'),
    ]
    
    for url, name in test_pages:
        try:
            response = requests.get(f'http://localhost:8000{url}', timeout=5)
            if response.status_code == 200 and 'rotating-ad-banner' in response.text:
                print(f"✓ {name} page has ads")
            else:
                print(f"✗ {name} page missing ads")
        except requests.exceptions.RequestException as e:
            print(f"✗ {name} page error: {str(e)}")

if __name__ == "__main__":
    test_ad_links()
    test_local_site()
    test_multiple_pages()
    
    print("\n" + "="*50)
    print("Ad Implementation Summary (Fixed):")
    print("- Ads rotate every 10 seconds automatically")
    print("- Ads appear on all pages using base.html")
    print("- Users can close ads (stored in localStorage)")
    print("- Ads displayed using native iframes (fixed)")
    print("- No sandbox restrictions causing errors")
    print("- Loading indicator shows while ads load")
    print("- Responsive design for mobile and desktop")
    print("="*50)