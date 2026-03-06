from django.db import migrations


class Migration(migrations.Migration):
    """
    Converts the `device.tags` column from PostgreSQL varchar[] (ArrayField) to
    jsonb (JSONField). The column was previously created as ArrayField but the
    model now uses JSONField for SQLite compatibility and richer querying.

    The SQL CAST converts each existing varchar[] value to a JSON array so no
    data is lost.
    """

    dependencies = [
        ("inventory", "0002_device_os_version_optional"),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
                ALTER TABLE device
                    ALTER COLUMN tags
                    TYPE jsonb
                    USING to_jsonb(tags);
            """,
            reverse_sql="""
                ALTER TABLE device
                    ALTER COLUMN tags
                    TYPE character varying[]
                    USING ARRAY(SELECT jsonb_array_elements_text(tags));
            """,
        ),
    ]
