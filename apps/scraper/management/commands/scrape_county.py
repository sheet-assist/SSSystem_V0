"""
Management command to scrape auction data for a specific county.

Usage:
    python manage.py scrape_county --state FL --county miamidade --type TD --date 2026-03-01
"""
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from datetime import datetime

from apps.locations.models import State, County
from apps.scraper.models import ScrapeJob
from apps.scraper.engine import run_scrape_job


class Command(BaseCommand):
    help = 'Scrape auction data for a specific county and date'

    def add_arguments(self, parser):
        parser.add_argument(
            '--state',
            type=str,
            required=True,
            help='State abbreviation (e.g., FL)'
        )
        parser.add_argument(
            '--county',
            type=str,
            required=True,
            help='County slug (e.g., miamidade)'
        )
        parser.add_argument(
            '--type',
            type=str,
            default='TD',
            choices=['TD', 'TL', 'SS', 'MF'],
            help='Prospect type: TD (Tax Deed), TL (Tax Lien), SS (Sheriff Sale), MF (Mortgage Foreclosure)'
        )
        parser.add_argument(
            '--date',
            type=str,
            required=True,
            help='Auction date (YYYY-MM-DD)'
        )

    def handle(self, *args, **options):
        state_abbr = options['state'].upper()
        county_slug = options['county'].lower()
        job_type = options['type']
        date_str = options['date']

        # Parse date
        try:
            target_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            raise CommandError(
                f'Invalid date format: {date_str}. Use YYYY-MM-DD'
            )

        # Get state
        try:
            state = State.objects.get(abbreviation__iexact=state_abbr, is_active=True)
        except State.DoesNotExist:
            raise CommandError(
                f'State {state_abbr} not found or inactive'
            )

        # Get county
        try:
            county = County.objects.get(
                slug__iexact=county_slug,
                state=state,
                is_active=True
            )
        except County.DoesNotExist:
            raise CommandError(
                f'County {county_slug} in {state_abbr} not found or inactive'
            )

        # Create or get existing job
        job, created = ScrapeJob.objects.get_or_create(
            county=county,
            job_type=job_type,
            target_date=target_date,
            defaults={'status': 'pending'}
        )

        if not created and job.status in ['running', 'completed']:
            self.stdout.write(
                self.style.WARNING(
                    f'Job already exists with status {job.status}. Skipping.'
                )
            )
            return

        self.stdout.write(
            f'Creating scrape job for {county.name}, {state.abbreviation} ({job_type}) on {target_date}'
        )
        self.stdout.write(f'Scrape Job ID: {job.pk}')

        # Run the scrape
        try:
            self.stdout.write('Starting scrape...')
            run_scrape_job(job)
            
            # Refresh to get updated stats
            job.refresh_from_db()
            
            self.stdout.write(
                self.style.SUCCESS(
                    f'\n✓ Scrape completed successfully!\n'
                    f'  Created: {job.prospects_created}\n'
                    f'  Updated: {job.prospects_updated}\n'
                    f'  Qualified: {job.prospects_qualified}\n'
                    f'  Disqualified: {job.prospects_disqualified}\n'
                    f'  Status: {job.status}'
                )
            )
        except Exception as e:
            job.refresh_from_db()
            self.stdout.write(
                self.style.ERROR(
                    f'\n✗ Scrape failed!\n'
                    f'  Error: {job.error_message}\n'
                    f'  Status: {job.status}'
                )
            )
            raise CommandError(f'Scrape job {job.pk} failed: {str(e)}')
            self.stdout.write(self.style.SUCCESS(
                f'Scrape completed: {job.prospects_created} created, '
                f'{job.prospects_updated} updated, {job.prospects_qualified} qualified'
            ))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Scrape failed: {str(e)}'))
