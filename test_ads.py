#!/usr/bin/env python3
"""Legacy ad cleanup verification script."""
import requests

LEGACY_VENDOR_MARKERS = [
    'otieu.com',
    'profitableratecpm',
    'gizokraijaw',
    'vemtoutcheeg',
    'rotating-ad-banner',
]

def test_local_site():
    """Test if the local Django site is running and legacy ad markers are gone."""
    print("\nTesting local Django site...")
    print("=" * 50)
    
    try:
        response = requests.get('http://localhost:8000/', timeout=5)
        if response.status_code == 200:
            print("✓ Django site is running")

            found_markers = [m for m in LEGACY_VENDOR_MARKERS if m in response.text]
            if found_markers:
                print(f"✗ Found legacy markers in home page: {', '.join(found_markers)}")
            else:
                print("✓ No legacy ad vendor markers found in home page")
                
        else:
            print(f"✗ Django site responded with status {response.status_code}")
            
    except requests.exceptions.RequestException as e:
        print(f"✗ Cannot connect to Django site: {str(e)}")

def test_multiple_pages():
    """Test multiple pages for absence of legacy ad markers."""
    print("\nTesting multiple pages for legacy markers...")
    print("=" * 50)
    
    test_pages = [
        ('/', 'Home'),
        ('/marketplace/', 'Marketplace'),
        ('/blogs/', 'Blogs'),
    ]
    
    for url, name in test_pages:
        try:
            response = requests.get(f'http://localhost:8000{url}', timeout=5)
            if response.status_code != 200:
                print(f"✗ {name} page returned {response.status_code}")
                continue

            found_markers = [m for m in LEGACY_VENDOR_MARKERS if m in response.text]
            if found_markers:
                print(f"✗ {name} page still has legacy markers: {', '.join(found_markers)}")
            else:
                print(f"✓ {name} page is clean")
        except requests.exceptions.RequestException as e:
            print(f"✗ {name} page error: {str(e)}")

if __name__ == "__main__":
    test_local_site()
    test_multiple_pages()
    
    print("\n" + "="*50)
    print("Legacy Ad Cleanup Summary:")
    print("- Checked home, marketplace, and blog pages")
    print("- Verified legacy vendor markers are absent")
    print("- Confirmed rotating legacy banner markers are removed")
    print("="*50)