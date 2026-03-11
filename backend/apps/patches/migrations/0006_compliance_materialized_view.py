"""
Migration: Create compliance_stats materialized view (Task 11.6)

The view precomputes per-device and fleet-wide compliance statistics.
Requires PostgreSQL — falls back gracefully on SQLite (dev/test).
"""
from django.db import migrations

CREATE_VIEW_SQL = """
CREATE MATERIALIZED VIEW IF NOT EXISTS mv_compliance_stats AS
SELECT
    COUNT(d.id)                                                AS total_devices,
    COUNT(d.id) FILTER (WHERE d.status = 'online')            AS online_devices,
    COUNT(d.id) FILTER (WHERE d.compliance_rate >= 90)        AS compliant_devices,
    COUNT(d.id) FILTER (WHERE d.compliance_rate < 90)         AS non_compliant_devices,
    COALESCE(AVG(d.compliance_rate), 0)                       AS avg_compliance_rate,

    (SELECT COUNT(DISTINCT dps.id)
     FROM device_patch_status dps
     JOIN patch p ON p.id = dps.patch_id
     WHERE dps.state = 'missing' AND p.severity = 'critical')  AS missing_critical_patches,

    (SELECT COUNT(DISTINCT dps.id)
     FROM device_patch_status dps
     JOIN patch p ON p.id = dps.patch_id
     WHERE dps.state = 'missing' AND p.severity = 'high')      AS missing_high_patches,

    json_build_object(
        'linux',   COUNT(d.id) FILTER (WHERE d.os_family = 'linux'),
        'windows', COUNT(d.id) FILTER (WHERE d.os_family = 'windows'),
        'macos',   COUNT(d.id) FILTER (WHERE d.os_family = 'macos')
    )                                                           AS devices_by_os,

    json_build_object(
        'production',  COUNT(d.id) FILTER (WHERE d.environment = 'production'),
        'staging',     COUNT(d.id) FILTER (WHERE d.environment = 'staging'),
        'development', COUNT(d.id) FILTER (WHERE d.environment = 'development'),
        'test',        COUNT(d.id) FILTER (WHERE d.environment = 'test')
    )                                                           AS devices_by_env,

    NOW()                                                       AS refreshed_at
FROM device d
WHERE d.status <> 'decommissioned';
"""

DROP_VIEW_SQL = "DROP MATERIALIZED VIEW IF EXISTS mv_compliance_stats;"

CREATE_INDEX_SQL = """
CREATE UNIQUE INDEX IF NOT EXISTS mv_compliance_stats_singleton
ON mv_compliance_stats ((1));
"""

DROP_INDEX_SQL = "DROP INDEX IF EXISTS mv_compliance_stats_singleton;"


class Migration(migrations.Migration):

    dependencies = [
        ("patches", "0005_compliancesnapshot"),
        ("inventory", "0001_initial"),
    ]

    operations = [
        migrations.RunSQL(
            sql=CREATE_VIEW_SQL + CREATE_INDEX_SQL,
            reverse_sql=DROP_INDEX_SQL + DROP_VIEW_SQL,
        ),
    ]
