# Quick Start: Testing Miami-Dade MF Scraper

## TL;DR - Run Scraper Now

### Step 1: Verify Configuration
```bash
python scraper_test_debug.py
```
✅ All tests pass? → Proceed to Step 2

### Step 2: Start Django Development Server
```bash
python manage.py runserver
```

### Step 3: Open Web Dashboard
- Go to: http://localhost:8000/scraper/dashboard/
- Click "Trigger New Scrape" (green button)

### Step 4: Configure Job
- **State:** Florida (FL)
- **County:** Miami-Dade
- **Type:** Mortgage Foreclosure (MF)
- **Date:** 03/15/2026 *(or any date with auctions)*
- Click "Create Job"

### Step 5: Run Job
- Find your job in the table
- Click green "Run" button
- **Watch progress bar animate!**
  - Shows real-time percentage
  - Shows current auction being processed
  - Updates stat counters live

### Step 6: Check Results
- When complete, see final counts
- Click "View" to see detailed results
- Click "View All Logs" to see debug information

---

## Test from Command Line

```bash
# Diagnostic test (doesn't scrape, just verifies config)
python scraper_test_debug.py

# Actual scraping (uses real Playwright browser)
python manage.py scrape_county --state FL --county miamidade --type MF --date 2026-03-15

# Django tests (unit tests)
.venv\Scripts\python.exe manage.py test apps.scraper.test_scraper_miami -v 2
```

---

## What's Tested?

| Component | Status | Test File |
|-----------|--------|-----------|
| County setup | ✅ PASS | `test_scraper_miami.py` |
| URL building | ✅ PASS | `test_scraper_miami.py` |
| HTML parsing | ✅ PASS | `test_scraper_miami.py` |
| Job creation | ✅ PASS | `test_scraper_miami.py` |
| Progress tracking | ✅ PASS | `test_scraper_miami.py` |
| Diagnostic checks | ✅ PASS | `scraper_test_debug.py` |

---

## If Scraping Fails

**Check logs at:** `/scraper/jobs/{job_id}/logs/`

**Common issues:**

| Error | Cause | Solution |
|-------|-------|----------|
| "No auctions found" | No auctions on that date | Pick different date |
| "Connection timeout" | Website unreachable | Check internet, retry later |
| "Failed to parse X" | HTML structure changed | Update parser in `parsers.py` |
| 0% progress after 60s | Selector not matching | Inspect website HTML manually |

---

## File Reference

| File | Purpose |
|------|---------|
| `scraper_test_debug.py` | Quick diagnostics script |
| `apps/scraper/test_scraper_miami.py` | Unit tests |
| `apps/scraper/engine.py` | Core scraper (Playwright automation) |
| `apps/scraper/parsers.py` | HTML → Prospect data parsing |
| `apps/scraper/models.py` | ScrapeJob, ScrapeLog models |
| `apps/scraper/views.py` | Dashboard, progress API |
| `SCRAPER_TESTING_GUIDE.md` | Detailed troubleshooting guide |

---

## Success Indicators

✅ **Diagnostic passed** - All config is correct
✅ **Job created** - You can create jobs in dashboard
✅ **Progress updates** - Progress bar moves while running
✅ **Logs generated** - Check logs for "Found X auctions"
✅ **Results saved** - Prospects created in database

---

## Dashboard URLs

```
Dashboard:        http://localhost:8000/scraper/dashboard/
Create Job:       http://localhost:8000/scraper/trigger/
Job Details:      http://localhost:8000/scraper/jobs/3/
Progress API:     http://localhost:8000/scraper/jobs/3/progress/
Job Logs:         http://localhost:8000/scraper/jobs/3/logs/
```

---

**Status:** ✅ Ready to test
**Date:** 2026-02-09
**Contact:** See SCRAPER_TESTING_GUIDE.md for detailed troubleshooting
