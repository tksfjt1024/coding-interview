from typing import Any

from rest_framework import serializers

from api.models import Category


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ["id", "company", "name", "parent_category", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        # self.instance は many=True の場合に list を取り得る型のため、単一インスタンスに絞り込む
        instance = self.instance if isinstance(self.instance, Category) else None

        # PATCH では未指定フィールドが attrs に含まれないため、既存インスタンスで補完して
        # 「更新後の状態」に対して検証する
        company = attrs.get("company", instance.company if instance else None)
        name = attrs.get("name", instance.name if instance else None)
        if "parent_category" in attrs:
            parent = attrs["parent_category"]
        else:
            parent = instance.parent_category if instance is not None else None

        if instance is not None and "company" in attrs and attrs["company"] != instance.company:
            # 会社をまたぐ付け替えを許すと、子カテゴリとの親子関係が
            # 「親子は同一会社」の不変条件を満たせなくなるため変更不可とする
            raise serializers.ValidationError({"company": "Company of an existing category cannot be changed."})

        if company is not None and name:
            # DRF 3.14 の ModelSerializer は Meta.constraints の UniqueConstraint から
            # バリデータを自動生成しない（unique_together のみ対応）。DB の IntegrityError に
            # 任せると 500 になるため、ここで明示的に検証して 400 を返す
            duplicates = Category.objects.filter(company=company, name=name)
            if instance is not None:
                duplicates = duplicates.exclude(pk=instance.pk)
            if duplicates.exists():
                raise serializers.ValidationError({"name": "A category with this name already exists in this company."})

        if parent is not None:
            if company is not None and parent.company_id != company.pk:
                raise serializers.ValidationError(
                    {"parent_category": "Parent category must belong to the same company."}
                )
            if instance is not None:
                if parent.pk == instance.pk:
                    raise serializers.ValidationError({"parent_category": "A category cannot be its own parent."})
                seen = {parent.pk}
                ancestor = parent.parent_category
                while ancestor is not None:
                    if ancestor.pk == instance.pk:
                        raise serializers.ValidationError(
                            {"parent_category": "This parent would create a circular reference."}
                        )
                    if ancestor.pk in seen:
                        # 既存データに循環が混入していても無限ループしないための防御
                        break
                    seen.add(ancestor.pk)
                    ancestor = ancestor.parent_category

        return attrs
