import logging

logger = logging.getLogger(__name__)


class DbRouter:
    def __init__(self):
        # Dynamically determine seikyu database routing based on available databases

        self.route_app_labels = {
            "admin": "default",
            "auth": "default",
            "contenttypes": "default",
            "sessions": "default",
            "messages": "default",
            "staticfiles": "default",
            "sfd": "postgres",
        }

    custom_models = ["iteminfo"]

    def _get_route_db(self, app_label, model_name):
        if model_name in self.custom_models:
            return "default"
        elif app_label in self.route_app_labels.keys():
            return self.route_app_labels[app_label]
        return "default"

    def db_for_read(self, model, **hints):
        routed_db = self._get_route_db(model._meta.app_label, model._meta.model_name)
        return routed_db

    def db_for_write(self, model, **hints):
        routed_db = self._get_route_db(model._meta.app_label, model._meta.model_name)
        return "default" if routed_db == "mcd2" else routed_db

    def allow_relation(self, obj1, obj2, **hints):
        db_for_obj1 = self._get_route_db(obj1._meta.model._meta.app_label, obj1._meta.model._meta.model_name)
        db_for_obj2 = self._get_route_db(obj2._meta.model._meta.app_label, obj2._meta.model._meta.model_name)
        return db_for_obj1 == db_for_obj2

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        routed_db = self._get_route_db(app_label, model_name)
        # logger.debug(f"db={db}, app_label={app_label}, model_name={model_name}, routed_db={routed_db})")
        if db == "default":
            return routed_db in {"default", "postgres"}
        elif db == "postgres":
            return routed_db in {"default", "postgres"}
        else:
            return db == routed_db
