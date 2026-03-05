class ReadReplicaRouter:
    """
    A router to control all database operations on models to route
    read-only traffic for specific apps to a read replica if available.
    """
    
    # Apps that heavily read and can tolerate slight replication lag
    ROUTE_APP_LABELS = {"patches", "deployments"}

    def db_for_read(self, model, **hints):
        """
        Attempts to read from 'readonly' DB if the model is in routed apps.
        Fallback to 'default'.
        """
        if model._meta.app_label in self.ROUTE_APP_LABELS:
            from django.conf import settings
            if "readonly" in settings.DATABASES:
                return "readonly"
        return "default"

    def db_for_write(self, model, **hints):
        """
        Always write to default.
        """
        return "default"

    def allow_relation(self, obj1, obj2, **hints):
        """
        Allow relations if a model in the same DB is involved.
        Since replica contains the same schema, returning True is safe.
        """
        return True

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        """
        Only run migrations against the master/default database.
        """
        return db == "default"
