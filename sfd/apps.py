from django.apps import AppConfig


class SfdConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "sfd"

    def ready(self):
        from sfd.common.font import register_japanese_fonts

        register_japanese_fonts()
