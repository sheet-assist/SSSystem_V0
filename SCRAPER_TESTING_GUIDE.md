# Miami-Dade MF Scraper - Testing & Troubleshooting Guide

## Overview
The scraper system is **fully configured and tested** for Miami-Dade County Mortgage Foreclosure (MF) scraping. All diagnostics pass successfully.

## Running the Scraper

### Method 1: Web Dashboard (Recommended)

1. **Navigate to Dashboard**
   - Go to: http://localhost:8000/scraper/dashboard/
   - or click "Scraper" → "Scraper Dashboard" in navbar

2. **Create a Scrape Job**
   - Click green "Trigger New Scrape" button
   - Select State: **Florida (FL)**
   - Select County: **Miami-Dade** (will auto-populate after selecting state)
   - Select Type: **Mortgage Foreclosure (MF)**
   - Enter Target Date: **03/15/2026** (must be valid upcoming date)
   - Click "Create Job"

3. **Run the Pending Job**
   - Job appears in table with "Pending" status
   - Click green "Run" button in the Action column
   - **Progress Bar** shows real-time scraping progress:
     - Percentage indicator (0-100%)
     - Current processing message
     - Live stat updates (created, updated, qualified, disqualified)

4. **Monitor Job**
   - Click "View" button to see detailed job status
   - Watch progress bar animate
   - See logs update in real-time
   - Page auto-reloads when job completes

### Method 2: Management Command

```bash
python manage.py scrape_county --state FL --county miamidade --type MF --date 2026-03-15
```

**Output example:**
```
[INFO] Creating/retrieving scrape job: Miami-Dade, 2026-03-15, MF
[INFO] Starting scrape job #3
[INFO] Navigating to https://miamidade.realforeclose.com/index.cfm?zaction=AUCTION&Zmethod=PREVIEW&AUCTIONDATE=03/15/2026
[INFO] Found 23 auctions on calendar page
Processing prospect 1/23: 2026-MF-100001
Processing prospect 2/23: 2026-MF-100002
...
[SUCCESS] Scrape completed: 23 found, 15 qualified, 8 disqualified
```

## Test Configuration Status

✅ **All tests passing:**

### Test 1: County Configuration
- ✓ Miami-Dade county created with all required fields
- ✓ State: Florida (FL)
- ✓ Foreclosure URL: https://miamidade.realforeclose.com
- ✓ Tax Deed URL: https://miamidade.realtaxdeed.com
- ✓ Supported types: TD, TL, MF, SS

### Test 2: Scrape Job Model
- ✓ Job creation with correct job_type='MF'
- ✓ Status transitions: pending → running → completed/failed
- ✓ Progress tracking fields: prospects_processed, total_prospects_found, progress_percent, progress_message
- ✓ Result counters: prospects_created, prospects_updated, prospects_qualified, prospects_disqualified

### Test 3: URL Building
- ✓ Correct base URL selection (foreclosure_url for MF)
- ✓ Calendar URL format: `/index.cfm?zaction=AUCTION&Zmethod=PREVIEW&AUCTIONDATE=MM/DD/YYYY`
- ✓ Date formatting: 03/15/2026 (MM/DD/YYYY)
- ✓ All URL components present

### Test 4: HTML Parser
- ✓ Extracts auction items (`.AUCTION_ITEM` divs)
- ✓ Parses case numbers
- ✓ Parses parcel IDs
- ✓ Parses property addresses
- ✓ Parses financial data (judgment amounts, assessed values)
- ✓ Handles canceled/postponed auctions
- ✓ Handles empty pages gracefully

## Troubleshooting

### Issue: Job shows "Pending" but won't run
**Cause:** Job not started manually
**Solution:** Click green "Run" button in dashboard

### Issue: Job shows "Running" forever
**Cause:** Website unreachable or timed out
**Solutions:**
1. Check job logs: Click "View" → "View All Logs"
2. Check internet connectivity
3. Verify realforeclose.com is accessible: https://miamidade.realforeclose.com
4. Check if website changed structure (selectors may need updating)

### Issue: "No auctions found for this date"
**Cause:** Valid date but no auctions scheduled
**Solutions:**
1. Select a different date with known auctions
2. Check realforeclose.com calendar directly for dates with auctions
3. Verify target_date is in YYYY-MM-DD format

### Issue: Auctions found but none qualified
**Cause:** Filter criteria too strict
**Solutions:**
1. Go to Settings → Filtering Criteria
2. Review min/max thresholds for Miami-Dade
3. Adjust filters to match expected property values
4. See settings_app/evaluation.py for evaluation logic

### Issue: "Connection timeout"
**Cause:** Website slow or temporarily unavailable
**Solutions:**
1. Retry job later
2. Check status of realforeclose.com
3. Try single county scrape instead of bulk

### Issue: Job failed with parse error
**Cause:** Website changed its HTML structure
**Solutions:**
1. Check job logs for specific parse error
2. Review HTML snapshot in logs
3. Update LABEL_REGEX_MAP in apps/scraper/parsers.py
4. Update CSS selectors if needed

## Running Tests

### Unit Tests
```bash
# All scraper tests
python manage.py test apps.scraper.test_scraper_miami -v 2

# Specific test class
python manage.py test apps.scraper.test_scraper_miami.ScraperURLBuildingTest -v 2

# Specific test method
python manage.py test apps.scraper.test_scraper_miami.ScraperURLBuildingTest.test_mortgage_foreclosure_url_building -v 2
```

### Diagnostic Script
```bash
# Run diagnostic tests (creates test data)
python scraper_test_debug.py
```

This creates real database records and verifies:
- Miami-Dade configuration
- Job creation
- URL building correctness
- HTML parser functionality

## Expected Behavior

### Successful Scrape Flow
```
1. User clicks "Run" on pending job
   ↓
2. Job status changes to "running"
3. Scraper navigates to realforeclose.com calendar page
4. Browser waits for .AUCTION_ITEM elements to load (20 sec timeout)
5. HTML parsed to extract auction data
6. For each auction:
   - Prospect record created or updated
   - Evaluated against FilterCriteria
   - Status set to qualified/disqualified
   - Progress bar updates
7. Job completed with results:
   - prospects_created: N
   - prospects_updated: M
   - prospects_qualified: X
   - prospects_disqualified: Y
8. Page auto-reloads
9. User sees "Completed" status with full results
```

### Progress Bar Updates
The progress bar updates every:
- **Backend:** After processing each prospect (10 prospects = 10 updates)
- **Frontend:** Every 1 second via JavaScript polling (fetches `/scraper/jobs/<id>/progress/`)

## Database Queries

### View Recent Jobs
```python
from apps.scraper.models import ScrapeJob

# All jobs
jobs = ScrapeJob.objects.all().order_by('-created_at')

# Completed jobs for Miami-Dade
jobs = ScrapeJob.objects.filter(
    county__slug='miamidade',
    status='completed'
).order_by('-created_at')

# Jobs with qualified prospects
jobs = ScrapeJob.objects.filter(
    prospects_qualified__gt=0
).order_by('-created_at')
```

### View Prospects from Scrape
```python
from apps.prospects.models import Prospect

# Prospects from recent Miami-Dade MF scrape
prospects = Prospect.objects.filter(
    county__slug='miamidade',
    prospect_type='MF',
    workflow_status='new'
).order_by('-created_at')

# Qualified prospects
qualified = prospects.filter(
    qualification_status='qualified'
)
```

### View Scrape Logs
```python
from apps.scraper.models import ScrapeLog

# Logs from job #3
logs = ScrapeLog.objects.filter(job_id=3).order_by('-created_at')

# Error logs only
errors = ScrapeLog.objects.filter(
    job_id=3,
    level='error'
)

print(errors.values('message', 'raw_html'))
```

## Configuration Files Involved

1. **Database Models:**
   - `apps/locations/models.py` - County with URLs
   - `apps/scraper/models.py` - ScrapeJob, ScrapeLog
   - `apps/prospects/models.py` - Prospect

2. **Engine:**
   - `apps/scraper/engine.py` - RealtdmScraper, run_scrape_job()
   - `apps/scraper/parsers.py` - HTML parsing logic

3. **Views & Routes:**
   - `apps/scraper/views.py` - Dashboard, trigger, detail, progress API
   - `apps/scraper/urls.py` - /scraper/dashboard/, /scraper/trigger/, /scraper/jobs/<id>/
   - `apps/scraper/forms.py` - ScrapeTriggerForm

4. **Templates:**
   - `templates/scraper/dashboard.html` - Job list with progress bars
   - `templates/scraper/trigger.html` - Job creation form
   - `templates/scraper/job_detail.html` - Detailed view with live progress

5. **Qualification Logic:**
   - `apps/settings_app/evaluation.py` - evaluate_prospect() function
   - `apps/settings_app/models.py` - FilterCriteria rules

## Quick Reference

**Dashboard URL:**
```
http://localhost:8000/scraper/dashboard/
```

**Job Detail URL:**
```
http://localhost:8000/scraper/jobs/{job_id}/
```

**Progress API (JSON):**
```
http://localhost:8000/scraper/jobs/{job_id}/progress/
```

**Example Response:**
```json
{
  "id": 3,
  "status": "running",
  "progress_percent": 45,
  "progress_message": "Processing prospect 10/23: 2026-MF-100010",
  "prospects_processed": 10,
  "total_prospects_found": 23,
  "prospects_created": 8,
  "prospects_updated": 2,
  "prospects_qualified": 5,
  "prospects_disqualified": 5,
  "error_message": ""
}
```

## Next Steps for Full Integration

1. ✅ Scraper engine configured
2. ✅ Miami-Dade county setup
3. ✅ Tests passing
4. ⏳ Live testing with real dates on realforeclose.com
5. ⏳ Prospect qualification tuning
6. ⏳ Batch scraping (multiple counties)
7. ⏳ Scheduled scraping (cron tasks)
8. ⏳ Email notifications on completion

---

**Last Updated:** 2026-02-09
**Test Status:** ✅ All tests passing
**Production Ready:** ✅ Yes (with test dates)
