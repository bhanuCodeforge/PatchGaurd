from django.db import migrations


class Migration(migrations.Migration):
    """
    Converts patch.cve_ids and patch.applicable_os columns from
    PostgreSQL varchar[] (legacy ArrayField) to jsonb (JSONField).
    """

    dependencies = [
        ("patches", "0001_initial"),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
                ALTER TABLE patch
                    ALTER COLUMN cve_ids
                    TYPE jsonb
                    USING to_jsonb(cve_ids);

                ALTER TABLE patch
                    ALTER COLUMN applicable_os
                    TYPE jsonb
                    USING to_jsonb(applicable_os);
            """,
            reverse_sql="""
                ALTER TABLE patch
                    ALTER COLUMN cve_ids
                    TYPE character varying[]
                    USING ARRAY(SELECT jsonb_array_elements_text(cve_ids));

                ALTER TABLE patch
                    ALTER COLUMN applicable_os
                    TYPE character varying[]
                    USING ARRAY(SELECT jsonb_array_elements_text(applicable_os));
            """,
        ),
    ]
