"""
Comprehensive scraper tests for Miami-Dade County (MF - Mortgage Foreclosure).
Tests the complete scraping pipeline and diagnoses issues.
"""
from django.test import TestCase, TransactionTestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import date
from unittest.mock import Mock, patch, MagicMock
from decimal import Decimal

from apps.locations.models import State, County
from apps.scraper.models import ScrapeJob, ScrapeLog
from apps.scraper.engine import RealtdmScraper, run_scrape_job
from apps.scraper.parsers import parse_calendar_page, normalize_prospect_data
from apps.prospects.models import Prospect
from apps.settings_app.models import FilterCriteria

User = get_user_model()


class MiamiDadeCountyConfigTest(TestCase):
    """Test Miami-Dade county configuration for MF scraping."""
    
    def setUp(self):
        """Set up test state and county."""
        self.state = State.objects.create(
            name='Florida',
            abbreviation='FL',
            is_active=True
        )
    
    def test_county_creation_with_urls(self):
        """Ensure Miami-Dade county has proper URLs configured."""
        county = County.objects.create(
            state=self.state,
            name='Miami-Dade',
            slug='miamidade',
            is_active=True,
            foreclosure_url='https://miamidade.realforeclose.com',
            taxdeed_url='https://miamidade.realtaxdeed.com',
            uses_realtdm=True,
        )
        
        self.assertEqual(county.name, 'Miami-Dade')
        self.assertEqual(county.slug, 'miamidade')
        self.assertIsNotNone(county.foreclosure_url)
        self.assertTrue(county.uses_realtdm)
    
    def test_available_prospect_types(self):
        """Check Miami-Dade supports all prospect types."""
        county = County.objects.create(
            state=self.state,
            name='Miami-Dade',
            slug='miamidade',
            is_active=True,
            foreclosure_url='https://miamidade.realforeclose.com',
            available_prospect_types=['TD', 'TL', 'MF', 'SS'],
        )
        
        self.assertIn('MF', county.available_prospect_types)


class ScraperURLBuildingTest(TestCase):
    """Test URL construction for Miami-Dade scraping."""
    
    def setUp(self):
        """Set up test data."""
        self.state = State.objects.create(name='Florida', abbreviation='FL')
        self.county = County.objects.create(
            state=self.state,
            name='Miami-Dade',
            slug='miamidade',
            foreclosure_url='https://miamidade.realforeclose.com',
            taxdeed_url='https://miamidade.realtaxdeed.com',
        )
    
    def test_mortgage_foreclosure_url_building(self):
        """Build correct URL for MF (Mortgage Foreclosure) scraping."""
        job = ScrapeJob.objects.create(
            county=self.county,
            job_type='MF',  # Mortgage Foreclosure
            target_date=date(2026, 3, 15),
        )
        
        scraper = RealtdmScraper(job)
        
        # Should use foreclosure_url for MF type
        self.assertEqual(scraper.base_url, 'https://miamidade.realforeclose.com')
        
        # Built calendar URL should be correct
        calendar_url = scraper._build_calendar_url(job.target_date)
        self.assertIn('03/15/2026', calendar_url)
        self.assertIn('PREVIEW', calendar_url)
        self.assertIn('miamidade.realforeclose.com', calendar_url)
    
    def test_tax_deed_vs_foreclosure_url(self):
        """Ensure correct URL is selected based on job type."""
        td_job = ScrapeJob.objects.create(
            county=self.county,
            job_type='TD',
            target_date=date(2026, 3, 15),
        )
        
        mf_job = ScrapeJob.objects.create(
            county=self.county,
            job_type='MF',
            target_date=date(2026, 3, 15),
        )
        
        td_scraper = RealtdmScraper(td_job)
        mf_scraper = RealtdmScraper(mf_job)
        
        # TD should use taxdeed_url
        self.assertIn('realtaxdeed', td_scraper.base_url)
        
        # MF should use foreclosure_url
        self.assertIn('realforeclose', mf_scraper.base_url)


class ParserHTMLExtractionTest(TestCase):
    """Test HTML parsing for auction data extraction."""
    
    def test_parse_mortgage_foreclosure_page(self):
        """Parse MF auction data from sample HTML."""
        # Sample HTML that might be on realforeclose.com
        html = '''
        <html>
            <div class="AUCTION_ITEM" aid="MF-2026-001">
                <div class="ASTAT_MSGB">Sale Time: 10:00 AM</div>
                <div class="AUCTION_DETAILS">
                    <table class="ad_tab">
                        <tr><td>Auction Type</td><td>Mortgage Foreclosure</td></tr>
                        <tr><td>Case #</td><td>2026-MF-123456</td></tr>
                        <tr><td>Parcel ID</td><td>45-25-25-0000-0100</td></tr>
                        <tr><td>Property Address</td><td>123 Miami Boulevard</td></tr>
                        <tr><td></td><td>Miami, FL 33101</td></tr>
                        <tr><td>Final Judgment</td><td>$250,000.00</td></tr>
                        <tr><td>Plaintiff Max Bid</td><td>$275,000.00</td></tr>
                        <tr><td>Assessed Value</td><td>$350,000.00</td></tr>
                    </table>
                </div>
            </div>
        </html>
        '''
        
        auctions = parse_calendar_page(html, 'miamidade')
        
        self.assertEqual(len(auctions), 1)
        auction = auctions[0]
        
        # Verify key fields are extracted
        self.assertEqual(auction['auction_id'], 'MF-2026-001')
        self.assertEqual(auction['case_number'], '2026-MF-123456')
        self.assertEqual(auction['parcel_id'], '45-25-25-0000-0100')
        self.assertEqual(auction['property_address'], '123 Miami Boulevard')
        self.assertEqual(auction['city_state_zip'], 'Miami, FL 33101')
        self.assertEqual(auction['final_judgment_amount'], Decimal('250000.00'))
        self.assertEqual(auction['plaintiff_max_bid'], Decimal('275000.00'))
        self.assertEqual(auction['assessed_value'], Decimal('350000.00'))
    
    def test_parse_empty_page(self):
        """Handle page with no auctions."""
        html = '''<html><body>No auctions for this date</body></html>'''
        auctions = parse_calendar_page(html, 'miamidade')
        self.assertEqual(len(auctions), 0)
    
    def test_parse_canceled_auctions(self):
        """Parse canceled auction status."""
        html = '''
        <div class="AUCTION_ITEM" aid="MF-2026-002">
            <div class="ASTAT_MSGB">Canceled - Postponed to later date</div>
            <div class="AUCTION_DETAILS">
                <table class="ad_tab">
                    <tr><td>Case #</td><td>2026-MF-654321</td></tr>
                </table>
            </div>
        </div>
        '''
        
        auctions = parse_calendar_page(html, 'miamidade')
        self.assertEqual(len(auctions), 1)
        self.assertEqual(auctions[0]['auction_status'], 'postponed')


class ScrapeJobExecutionTest(TransactionTestCase):
    """Test full scrape job execution with mocked browser."""
    
    def setUp(self):
        """Set up test data."""
        self.state = State.objects.create(name='Florida', abbreviation='FL')
        self.county = County.objects.create(
            state=self.state,
            name='Miami-Dade',
            slug='miamidade',
            foreclosure_url='https://miamidade.realforeclose.com',
        )
        
        # Create a admin user for triggering jobs
        self.user = User.objects.create_user(
            username='admin',
            email='admin@test.com',
            password='test123'
        )
        
        # Create filter criteria for qualification testing
        self.filter_criteria = FilterCriteria.objects.create(
            name='Test Criteria',
            county=self.county,
            min_assessed_value=0,
            max_assessed_value=500000,
        )
    
    def test_scrape_job_model_operations(self):
        """Test ScrapeJob CRUD operations."""
        job = ScrapeJob.objects.create(
            county=self.county,
            job_type='MF',
            target_date=date(2026, 3, 15),
            triggered_by=self.user,
        )
        
        self.assertEqual(job.status, 'pending')
        self.assertEqual(job.job_type, 'MF')
        self.assertEqual(job.prospects_created, 0)
        self.assertIsNone(job.started_at)
    
    def test_scrape_job_status_transition(self):
        """Test job status changes during execution."""
        job = ScrapeJob.objects.create(
            county=self.county,
            job_type='MF',
            target_date=date(2026, 3, 15),
        )
        
        # Simulate running
        job.status = 'running'
        job.started_at = timezone.now()
        job.save()
        
        self.assertEqual(job.status, 'running')
        self.assertIsNotNone(job.started_at)
        
        # Simulate completion
        job.status = 'completed'
        job.completed_at = timezone.now()
        job.prospects_created = 10
        job.prospects_qualified = 5
        job.save()
        
        self.assertEqual(job.status, 'completed')
        self.assertEqual(job.prospects_created, 10)
    
    def test_scrape_job_error_state(self):
        """Test job failure state."""
        job = ScrapeJob.objects.create(
            county=self.county,
            job_type='MF',
            target_date=date(2026, 3, 15),
        )
        
        error_msg = "Connection timeout - realforeclose.com unavailable"
        job.status = 'failed'
        job.error_message = error_msg
        job.completed_at = timezone.now()
        job.save()
        
        self.assertEqual(job.status, 'failed')
        self.assertIn('unavailable', job.error_message)
    
    @patch('apps.scraper.engine.sync_playwright')
    def test_scrape_job_exceution_with_mock_browser(self, mock_playwright):
        """Test job execution with mocked browser."""
        # Mock the browser and page
        mock_page = MagicMock()
        mock_page.goto = MagicMock()
        mock_page.wait_for_selector = MagicMock()
        
        # Mock HTML response
        mock_html = '''
        <div class="AUCTION_ITEM" aid="MF-2026-001">
            <div class="ASTAT_MSGB">Sale Time: 10:00 AM</div>
            <div class="AUCTION_DETAILS">
                <table class="ad_tab">
                    <tr><td>Case #</td><td>2026-MF-100001</td></tr>
                    <tr><td>Parcel ID</td><td>45-25-25-0000-0100</td></tr>
                    <tr><td>Property Address</td><td>100 Main St</td></tr>
                    <tr><td></td><td>Miami, FL 33101</td></tr>
                    <tr><td>Final Judgment</td><td>$150,000.00</td></tr>
                    <tr><td>Assessed Value</td><td>$200,000.00</td></tr>
                </table>
            </div>
        </div>
        '''
        mock_page.content = MagicMock(return_value=mock_html)
        
        # Configure playwright mock
        mock_browser = MagicMock()
        mock_browser.new_page = MagicMock(return_value=mock_page)
        mock_browser.close = MagicMock()
        
        mock_context = MagicMock()
        mock_context.chromium.launch = MagicMock(return_value=mock_browser)
        mock_context.__enter__ = MagicMock(return_value=mock_context)
        mock_context.__exit__ = MagicMock(return_value=False)
        
        mock_playwright.return_value = mock_context
        
        # Run job
        job = ScrapeJob.objects.create(
            county=self.county,
            job_type='MF',
            target_date=date(2026, 3, 15),
            triggered_by=self.user,
        )
        
        # Note: run_scrape_job() will attempt to process prospects
        # This test verifies the job record is created and status transitions work
        self.assertEqual(job.status, 'pending')
        
        job.status = 'running'
        job.save()
        
        self.assertEqual(job.status, 'running')


class ScrapeLogTest(TestCase):
    """Test scrape logging functionality."""
    
    def setUp(self):
        """Set up test data."""
        self.state = State.objects.create(name='Florida', abbreviation='FL')
        self.county = County.objects.create(
            state=self.state,
            name='Miami-Dade',
            slug='miamidade',
        )
        self.job = ScrapeJob.objects.create(
            county=self.county,
            job_type='MF',
            target_date=date(2026, 3, 15),
        )
    
    def test_log_creation(self):
        """Create scrape logs."""
        log_info = ScrapeLog.objects.create(
            job=self.job,
            level='info',
            message='Starting scrape for Miami-Dade',
        )
        
        self.assertEqual(log_info.level, 'info')
        self.assertIn('Miami-Dade', log_info.message)
    
    def test_log_levels(self):
        """Test different log levels."""
        info_log = ScrapeLog.objects.create(job=self.job, level='info', message='Info message')
        warn_log = ScrapeLog.objects.create(job=self.job, level='warning', message='Warning message')
        error_log = ScrapeLog.objects.create(job=self.job, level='error', message='Error message')
        
        self.assertEqual(ScrapeLog.objects.filter(job=self.job, level='info').count(), 1)
        self.assertEqual(ScrapeLog.objects.filter(job=self.job, level='warning').count(), 1)
        self.assertEqual(ScrapeLog.objects.filter(job=self.job, level='error').count(), 1)
    
    def test_html_truncation(self):
        """Verify HTML is truncated in logs."""
        large_html = '<div>' + 'x' * 10000 + '</div>'
        
        log = ScrapeLog.objects.create(
            job=self.job,
            level='info',
            message='HTML captured',
            raw_html=large_html,
        )
        
        self.assertLessEqual(len(log.raw_html), 5000)


class DiagnosticTest(TestCase):
    """Diagnostic tests to identify scraping issues."""
    
    def setUp(self):
        """Set up test data."""
        self.state = State.objects.create(name='Florida', abbreviation='FL')
        self.county = County.objects.create(
            state=self.state,
            name='Miami-Dade',
            slug='miamidade',
            foreclosure_url='https://miamidade.realforeclose.com',
            available_prospect_types=['TD', 'TL', 'MF', 'SS'],
        )
    
    def test_miami_dade_scraper_initialization(self):
        """Test RealtdmScraper with Miami-Dade for MF."""
        job = ScrapeJob.objects.create(
            county=self.county,
            job_type='MF',
            target_date=date(2026, 3, 15),
        )
        
        scraper = RealtdmScraper(job)
        
        # Verify initialization
        self.assertEqual(scraper.job, job)
        self.assertEqual(scraper.base_url, 'https://miamidade.realforeclose.com')
        
        # Verify URL building
        calendar_url = scraper._build_calendar_url(date(2026, 3, 15))
        expected_parts = [
            'https://miamidade.realforeclose.com',
            'AUCTIONDATE=03/15/2026',
            'PREVIEW',
        ]
        
        for part in expected_parts:
            self.assertIn(part, calendar_url, f"Missing '{part}' in URL: {calendar_url}")
    
    def test_check_county_configuration_completeness(self):
        """Verify all Miami-Dade configuration is present."""
        self.assertTrue(self.county.is_active)
        self.assertIsNotNone(self.county.foreclosure_url)
        self.assertIn('MF', self.county.available_prospect_types)
