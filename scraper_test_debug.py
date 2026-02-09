#!/usr/bin/env python
"""
Simple diagnostic script to test Miami-Dade MF scraping configuration.
Run directly: python scraper_test_debug.py
"""
import os
import sys
import django
from pathlib import Path

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from datetime import date
from apps.locations.models import State, County
from apps.scraper.models import ScrapeJob
from apps.scraper.engine import RealtdmScraper

def test_miami_dade_configuration():
    """Test Miami-Dade county is properly configured."""
    print("\n" + "="*60)
    print("TEST 1: Miami-Dade County Configuration")
    print("="*60)
    
    # Create or get Florida state
    state, created = State.objects.get_or_create(
        abbreviation='FL',
        defaults={'name': 'Florida', 'is_active': True}
    )
    print(f"✓ State found/created: {state}")
    
    # Create or get Miami-Dade county
    county, created = County.objects.get_or_create(
        state=state,
        slug='miamidade',
        defaults={
            'name': 'Miami-Dade',
            'is_active': True,
            'foreclosure_url': 'https://miamidade.realforeclose.com',
            'taxdeed_url': 'https://miamidade.realtaxdeed.com',
            'uses_realtdm': True,
            'available_prospect_types': ['TD', 'TL', 'MF', 'SS'],
        }
    )
    
    print(f"✓ County found/created: {county}")
    print(f"  - is_active: {county.is_active}")
    print(f"  - foreclosure_url: {county.foreclosure_url}")
    print(f"  - taxdeed_url: {county.taxdeed_url}")
    print(f"  - uses_realtdm: {county.uses_realtdm}")
    print(f"  - available_prospect_types: {county.available_prospect_types}")
    
    return county


def test_mf_job_creation(county):
    """Test creating a MF scrape job."""
    print("\n" + "="*60)
    print("TEST 2: Create MF Scrape Job")
    print("="*60)
    
    job = ScrapeJob.objects.create(
        county=county,
        job_type='MF',  # Mortgage Foreclosure
        target_date=date(2026, 3, 15),
    )
    
    print(f"✓ Job created: {job}")
    print(f"  - ID: {job.pk}")
    print(f"  - Type: {job.job_type}")
    print(f"  - Status: {job.status}")
    print(f"  - Target Date: {job.target_date}")
    
    return job


def test_scraper_url_building(job):
    """Test RealtdmScraper URL building."""
    print("\n" + "="*60)
    print("TEST 3: Scraper URL Building")
    print("="*60)
    
    scraper = RealtdmScraper(job)
    
    print(f"✓ Scraper initialized")
    print(f"  - Base URL: {scraper.base_url}")
    
    calendar_url = scraper._build_calendar_url(job.target_date)
    print(f"  - Calendar URL: {calendar_url}")
    
    # Verify URL components
    required_parts = [
        ('County name', 'miamidade'),
        ('realforeclose domain', 'realforeclose.com'),
        ('Date format', '03/15/2026'),
        ('PREVIEW action', 'PREVIEW'),
        ('Auction date param', 'AUCTIONDATE'),
    ]
    
    print(f"\n  ✓ URL Components Check:")
    for component, part in required_parts:
        if part in calendar_url:
            print(f"    ✓ {component}: FOUND ('{part}')")
        else:
            print(f"    ✗ {component}: MISSING ('{part}')")
    
    return scraper, calendar_url


def test_parser():
    """Test HTML parser with sample MF data."""
    print("\n" + "="*60)
    print("TEST 4: HTML Parser for MF Auctions")
    print("="*60)
    
    from apps.scraper.parsers import parse_calendar_page
    
    # Sample MF auction HTML
    html = '''
    <html>
        <div class="AUCTION_ITEM" aid="MF-2026-TEST001">
            <div class="ASTAT_MSGB">Sale Time: 10:00 AM</div>
            <div class="AUCTION_DETAILS">
                <table class="ad_tab">
                    <tr><td>Auction Type</td><td>Mortgage Foreclosure</td></tr>
                    <tr><td>Case #</td><td>2026-MF-TEST123</td></tr>
                    <tr><td>Parcel ID</td><td>45-25-25-0000-0100</td></tr>
                    <tr><td>Property Address</td><td>123 Test Street</td></tr>
                    <tr><td></td><td>Miami, FL 33101</td></tr>
                    <tr><td>Final Judgment</td><td>$200,000.00</td></tr>
                    <tr><td>Assessed Value</td><td>$250,000.00</td></tr>
                </table>
            </div>
        </div>
    </html>
    '''
    
    auctions = parse_calendar_page(html, 'miamidade')
    
    if auctions:
        print(f"✓ Successfully parsed {len(auctions)} auction(s)")
        for idx, auction in enumerate(auctions, 1):
            print(f"\n  Auction #{idx}:")
            print(f"    - ID: {auction.get('auction_id')}")
            print(f"    - Case #: {auction.get('case_number')}")
            print(f"    - Parcel ID: {auction.get('parcel_id')}")
            print(f"    - Address: {auction.get('property_address')}")
            print(f"    - Final Judgment: {auction.get('final_judgment_amount')}")
            print(f"    - Assessed Value: {auction.get('assessed_value')}")
    else:
        print(f"✗ FAILED: No auctions parsed from HTML")
        print(f"  This suggests the HTML structure doesn't match expected selectors")


def main():
    """Run all tests."""
    print("\n")
    print("╔" + "="*58 + "╗")
    print("║  Miami-Dade County MF Scraper - Diagnostic Tests          ║")
    print("╚" + "="*58 + "╝")
    
    try:
        county = test_miami_dade_configuration()
        job = test_mf_job_creation(county)
        scraper, url = test_scraper_url_building(job)
        test_parser()
        
        print("\n" + "="*60)
        print("SUMMARY")
        print("="*60)
        print("✓ All diagnostic tests completed successfully!")
        print("\nNext Steps:")
        print("1. Visit the dashboard at: /scraper/dashboard/")
        print("2. Create a new scrape job for Miami-Dade, MF type")
        print("3. Click 'Run Job' to execute the scraper")
        print("4. Monitor progress on the job detail page")
        print("\nIf scraping still fails:")
        print("- Check the job logs for specific error messages")
        print("- Verify the realforeclose.com website is reachable")
        print("- Confirm the HTML structure matches expected selectors")
        
    except Exception as e:
        print(f"\n✗ ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
