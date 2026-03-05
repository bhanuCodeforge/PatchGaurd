from celery import shared_task
from django.db import connection
from datetime import datetime
from dateutil.relativedelta import relativedelta
import structlog

logger = structlog.get_logger(__name__)

@shared_task
def cleanup_audit_partitions():
    """
    Creates partition for next month if it doesn't exist.
    Drops partitions older than 12 months.
    Runs monthly via Celery Beat.
    """
    now = datetime.now()
    
    # Calculate next month
    next_month = now + relativedelta(months=1)
    
    # Calculate 12 months ago
    twelve_months_ago = now - relativedelta(months=12)
    
    logger.info("Starting audit_log partition maintenance", 
                creating_for=next_month.strftime('%Y_%m'),
                dropping_older_than=twelve_months_ago.strftime('%Y_%m'))

    with connection.cursor() as cursor:
        # Create next month's partition
        cursor.execute("SELECT create_monthly_partition(%s, %s);", [next_month.year, next_month.month])
        
        # Drop old partitions
        # Assuming partition naming convention is audit_log_YYYY_MM
        cursor.execute("""
            SELECT relname
            FROM pg_class
            WHERE relname LIKE 'audit_log_%'
              AND relkind = 'r'
              AND relispartition = true;
        """)
        
        partitions = cursor.fetchall()
        for (part_name,) in partitions:
            try:
                # Extract year and month from name like 'audit_log_2024_05'
                parts = part_name.split('_')
                if len(parts) == 4 and parts[0] == 'audit' and parts[1] == 'log':
                    p_year = int(parts[2])
                    p_month = int(parts[3])
                    p_date = datetime(p_year, p_month, 1)
                    
                    if p_date < datetime(twelve_months_ago.year, twelve_months_ago.month, 1):
                        logger.info("Dropping old partition", partition=part_name)
                        cursor.execute(f"DROP TABLE {part_name};")
            except Exception as e:
                logger.error("Failed to parse or drop partition", partition=part_name, error=str(e))
                
    logger.info("Audit_log partition maintenance complete")

try:
    import ldap
except ImportError:
    ldap = None

from django.conf import settings
from .models import User, AuditLog

@shared_task
def sync_ldap_users():
    if not getattr(settings, 'LDAP_SYNC_ENABLED', False):
        return

    ldap_uri = getattr(settings, 'LDAP_URI', '')
    service_dn = getattr(settings, 'LDAP_SERVICE_DN', '')
    service_password = getattr(settings, 'LDAP_SERVICE_PASSWORD', '')
    search_base = getattr(settings, 'LDAP_SEARCH_BASE', '')

    if not all([ldap_uri, service_dn, service_password, search_base]):
        logger.error("Missing LDAP configuration for sync")
        return

    logger.info("LDAP Sync Started")
    # Actual implementation would page through AD and sync

@shared_task
def test_ldap_connection():
    ldap_uri = getattr(settings, 'LDAP_URI', '')
    if not ldap_uri:
        return False
    try:
        conn = ldap.initialize(ldap_uri)
        conn.set_option(ldap.OPT_NETWORK_TIMEOUT, 5.0)
        conn.simple_bind_s()
        return True
    except Exception as e:
        logger.error(f"LDAP Test Connection Failed: {e}")
        return False
