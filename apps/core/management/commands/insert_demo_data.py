"""
Management command wrapper for insert_demo_data.py
Usage: python manage.py insert_demo_data

Original file was at project root. Wrapped as a management command
for proper Django integration.
"""

from django.core.management.base import BaseCommand



class Command(BaseCommand):
    help = 'Insert demo data into the database (migrated from root-level script)'

    def handle(self, *args, **options):
        self.stdout.write('Running insert_demo_data...')
        # NOTE: Review and update this to use proper Django imports
        # The original script logic should be integrated here
        self.stdout.write(self.style.WARNING(
            'TODO: Migrate the logic from the original insert_demo_data.py into this command. '
            'The original file has been preserved at core/insert_demo_data_original.py'
        ))
