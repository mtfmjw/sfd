from django.db import models
from django.forms import ValidationError
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


def default_valid_from_date():
    """Return current date for default valid_from."""
    return timezone.now().date() + timezone.timedelta(days=1)


def default_valid_to_date():
    """Return maximum date for default valid_to."""
    return timezone.datetime(2222, 12, 31).date()


class BaseModel(models.Model):
    """作成者、作成日時、更新者、更新日時、削除フラグを持つベースモデル
    更新：更新日時による楽観的排他制御を行う。
    削除：削除フラグを立てて論理削除を行う。物理削除は行わない。
    ユニックキー：楽観的排他制御を行うために、継承モデルはユニックキーをセットする必要がある。
    """

    created_by = models.CharField(max_length=150, blank=True, null=True, verbose_name=_("Created By"))
    created_at = models.DateTimeField(verbose_name=_("Created At"), auto_now_add=True)
    updated_by = models.CharField(max_length=150, blank=True, null=True, verbose_name=_("Updated By"))
    updated_at = models.DateTimeField(verbose_name=_("Updated At"), auto_now=True)
    deleted_flg = models.BooleanField(default=False, verbose_name=_("Delete Flag"))

    class Meta:
        abstract = True

    @classmethod
    def get_unique_field_names(cls) -> list[str]:
        # Get first UniqueConstraint in Meta.constraints
        for constraint in cls._meta.constraints:
            if isinstance(constraint, models.UniqueConstraint):
                return list(constraint.fields)

        # Get first unique_together constraint
        if cls._meta.unique_together:
            return list(cls._meta.unique_together[0])

        # Get first field with unique=True
        for field in cls._meta.get_fields():
            if getattr(field, "unique", False) and field.name != "id":
                return [field.name]

        return []

    @classmethod
    def get_base_model_fields(cls) -> list[models.Field]:
        """BaseModelのフィールド名を取得"""
        return [cls._meta.get_field(name) for name in ("created_by", "created_at", "updated_by", "updated_at", "deleted_flg")]

    @classmethod
    def get_local_concrete_fields(cls) -> list[models.Field]:
        """継承モデルのフィールド名を取得"""
        base_model_fields = cls.get_base_model_fields()
        return [f for f in cls._meta.get_fields() if f not in base_model_fields and not f.auto_created and f.concrete]  # type: ignore[misc]


class MasterModel(BaseModel):
    """有効期間で管理するマスタモデル
    有効期間：重複不可、歯抜け可能、初回作成時のみ開始日を過去日(今日含め)に設定可能
        過去日(今日含め)レコードが存在する場合、新規レコードの開始日は未来日のみ設定可能
    更新：
        - 有効期間の開始日が過去のものは更新不可、更新するにはコピー機能で未来有効開始日を指定して新規作成する、その際元の終了日は自動調整される
        - 有効期間の開始日が未来日のものは更新可能、有効期間開始日もほかの有効期間と重複しない限り過去日にも変更可能
    削除：論理削除のみ、有効期間の開始日が過去のものは削除不可; 一覧画面よりバッチ削除は不可
    """

    valid_from = models.DateField(_("Valid From"), default=default_valid_from_date)
    valid_to = models.DateField(_("Valid To"), blank=True, default=default_valid_to_date)

    class Meta:  # type: ignore[misc]
        abstract = True

    @classmethod
    def get_master_model_fields(cls) -> list[models.Field]:
        return [cls._meta.get_field(f) for f in ("valid_from", "valid_to")]

    @classmethod
    def get_local_concrete_fields(cls) -> list[models.Field]:
        """継承モデルのフィールド名を取得"""
        local_fields = super().get_local_concrete_fields()
        master_fields = cls.get_master_model_fields()
        return [f for f in local_fields if f not in master_fields and not f.auto_created and f.concrete]  # type: ignore[misc]

    @classmethod
    def get_unique_fields_without_valid_from(cls):
        """同一マスタレコードを特定するためのユニークフィールド(valid_fromを除く)を取得"""
        return (f for f in cls.get_unique_field_names() if f != "valid_from")

    def get_previous_instance(self):
        """Get the previous instance based on valid_from and unique fields."""
        filter_kwargs = {key: getattr(self, key) for key in self.get_unique_fields_without_valid_from()}
        if not filter_kwargs:
            return None
        previous = self.__class__.objects.filter(**filter_kwargs, valid_from__lt=self.valid_from).order_by("-valid_from").first()
        return previous

    def get_next_instance(self):
        """Get the next instance based on valid_from and unique fields."""
        filter_kwargs = {key: getattr(self, key) for key in self.get_unique_fields_without_valid_from()}
        if not filter_kwargs:
            return None
        next = self.__class__.objects.filter(**filter_kwargs, valid_from__gt=self.valid_from).order_by("valid_from").first()
        return next

    def clean(self):
        super().clean()
        if self.valid_from and self.valid_to and self.valid_to < self.valid_from:
            raise ValidationError({"valid_to": _("Valid To must be greater than or equal to Valid From")})

    def save(self, force_insert=False, force_update=False, using=None, update_fields=None):
        previous = self.get_previous_instance()
        if previous and previous.pk != self.pk and previous.valid_to >= self.valid_from:
            previous.valid_to = self.valid_from - timezone.timedelta(days=1)
            previous.updated_by = self.updated_by
            previous.updated_at = timezone.now()
            previous.save()

        next = self.get_next_instance()
        if next and next.pk != self.pk and next.valid_from <= self.valid_to:
            self.valid_to = next.valid_from - timezone.timedelta(days=1)

        if self.valid_to is None:
            self.valid_to = default_valid_to_date()
        return super().save(force_insert=force_insert, force_update=force_update, using=using, update_fields=update_fields)
