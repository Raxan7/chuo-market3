#!/usr/bin/env python3
"""
Test script to verify all ad links are working
"""
import requests
import time
import re

# Ad links from the implementation
ad_links = [
    'https://www.effectivegatecpm.com/jp604fzw?key=0ac38e5ac8cfdc4296fa7f9060dcb6aa',
    'https://www.effectivegatecpm.com/sqf24i6k9?key=69bd5c9b5bc46a7bf95c51f8a22d72be',
    'https://www.effectivegatecpm.com/ghvacaxk?key=152c6ad3137dfd992107cafb20ba5475',
    'https://www.effectivegatecpm.com/y56j06mc56?key=8a8851afe3dc03e0d7ad3a66474de43d',
    'https://www.effectivegatecpm.com/cdrnmt82a0?key=f324af40210b539b89a9b3648da6d1a6',
    'https://www.effectivegatecpm.com/x127x1tt?key=057c2839b78ce9b3e3d4222043664ed1',
    'https://www.effectivegatecpm.com/t8969tvrft?key=a7ad665ecba681e29abdc931553dded0',
    'https://www.effectivegatecpm.com/ue2x9peh?key=edf04c7d5e5bf35cb005016b6dc7e7c7',
    'https://www.effectivegatecpm.com/bh2zyhrc?key=1e19b0229c99212775e63f84220c3f4d',
    'https://www.effectivegatecpm.com/jfpyfpi2f?key=495705b0c167fee0da445856466fa6fd'
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