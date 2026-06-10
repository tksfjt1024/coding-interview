from django.db import IntegrityError, transaction
from rest_framework import serializers, viewsets
from rest_framework.serializers import BaseSerializer

from api.models import Category
from api.serializers import CategorySerializer


class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer

    def perform_create(self, serializer: BaseSerializer) -> None:
        self._save_handling_db_conflict(serializer)

    def perform_update(self, serializer: BaseSerializer) -> None:
        self._save_handling_db_conflict(serializer)

    def _save_handling_db_conflict(self, serializer: BaseSerializer) -> None:
        # serializer の事前検証は、同時リクエスト間の競合（検証通過後に同名カテゴリが
        # commit される等）までは防げない。DB 制約違反を最終防衛として 400 に変換する。
        # atomic（savepoint）の内側で save することで、失敗時も外側のトランザクションを壊さない
        try:
            with transaction.atomic():
                serializer.save()
        except IntegrityError as exc:
            raise serializers.ValidationError("Request conflicts with data committed by another request.") from exc
