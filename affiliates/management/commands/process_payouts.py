# affiliates/management/commands/process_payouts.py
from django.core.management.base import BaseCommand
from django.utils import timezone
from affiliates.models import PayoutRequest, Affiliate
from django.conf import settings
from decimal import Decimal
import csv
import os

class Command(BaseCommand):
    help = 'Process affiliate payouts that are approved and generate CSV reports'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Run in dry-run mode (no actual changes)',
        )
        parser.add_argument(
            '--status',
            type=str,
            default='approved',
            help='Status of payouts to process (approved, pending, all)',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        status = options['status'].lower()
        
        # Set up filtering based on status
        if status == 'all':
            payout_requests = PayoutRequest.objects.exclude(status='paid')
        else:
            payout_requests = PayoutRequest.objects.filter(status=status)
        
        self.stdout.write(f"Found {payout_requests.count()} payout requests to process")
        
        if not payout_requests.exists():
            self.stdout.write(self.style.WARNING("No payout requests found to process"))
            return
        
        # Generate CSV file for accounting
        timestamp = timezone.now().strftime("%Y%m%d_%H%M%S")
        filename = f"affiliate_payouts_{timestamp}.csv"
        file_path = os.path.join(settings.MEDIA_ROOT, 'reports', filename)
        
        # Ensure directory exists
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        # Process payouts and write CSV
        with open(file_path, 'w', newline='') as csvfile:
            fieldnames = ['affiliate_id', 'username', 'full_name', 'amount', 
                         'payment_method', 'payment_details', 'request_date', 'status']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            
            total_amount = Decimal('0.00')
            processed_count = 0
            
            for payout in payout_requests:
                affiliate = payout.affiliate
                user = affiliate.user
                
                # Write to CSV
                writer.writerow({
                    'affiliate_id': affiliate.id,
                    'username': user.username,
                    'full_name': f"{user.first_name} {user.last_name}".strip() or user.username,
                    'amount': payout.amount,
                    'payment_method': payout.payment_method,
                    'payment_details': payout.payment_details,
                    'request_date': payout.requested_at.strftime("%Y-%m-%d"),
                    'status': payout.status
                })
                
                # Process payout if not dry run
                if not dry_run and status == 'approved':
                    # Mark as paid
                    payout.status = 'paid'
                    payout.processed_at = timezone.now()
                    payout.save()
                    
                    # Update affiliate balance
                    affiliate.balance -= payout.amount
                    affiliate.total_paid += payout.amount
                    affiliate.save()
                    
                    processed_count += 1
                    total_amount += payout.amount
            
        if dry_run:
            self.stdout.write(
                self.style.SUCCESS(f"Dry run completed. CSV report generated at {file_path}")
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Processed {processed_count} payouts totaling {total_amount}. "
                    f"CSV report generated at {file_path}"
                )
            )