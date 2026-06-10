import uuid
from unittest import mock

from rest_framework import status
from rest_framework.test import APITestCase

from api.models import Category, Company
from api.serializers import CategorySerializer


class CategoryViewTests(APITestCase):
    def setUp(self):
        self.company_a = Company.objects.create(name="Company A")
        self.company_b = Company.objects.create(name="Company B")

    def _create_category(self, company, name, parent=None):
        return Category.objects.create(company=company, name=name, parent_category=parent)

    # ---- list ----

    def test_list(self):
        """登録済みのカテゴリが、会社をまたいで全件返る。"""
        food = self._create_category(self.company_a, "食品")
        book = self._create_category(self.company_b, "書籍")

        response = self.client.get("/api/categories/", format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        body = response.json()
        self.assertEqual(len(body), 2)
        # モデルに既定の並び順が無いため、順序には依存せず集合で検証する
        self.assertEqual(
            {item["id"] for item in body},
            {str(food.id), str(book.id)},
        )

    def test_list_returns_empty_list_when_no_categories(self):
        """カテゴリが存在しない場合、空のリストが返る。"""
        response = self.client.get("/api/categories/", format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json(), [])

    # ---- retrieve ----

    def test_retrieve(self):
        """カテゴリの詳細が、定義したフィールドすべてを含んで返る。"""
        parent = self._create_category(self.company_a, "食品")
        child = self._create_category(self.company_a, "生鮮食品", parent=parent)

        response = self.client.get(f"/api/categories/{child.id}/", format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        body = response.json()
        self.assertEqual(body["id"], str(child.id))
        self.assertEqual(body["company"], str(self.company_a.id))
        self.assertEqual(body["name"], "生鮮食品")
        self.assertEqual(body["parent_category"], str(parent.id))
        self.assertIsNotNone(body["created_at"])
        self.assertIsNotNone(body["updated_at"])

    def test_retrieve_returns_404_for_unknown_id(self):
        """存在しない ID を指定すると 404 が返る。"""
        response = self.client.get(f"/api/categories/{uuid.uuid4()}/", format="json")

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_retrieve_returns_404_for_malformed_id(self):
        """UUID 形式でない ID を指定すると 404 が返る。"""
        response = self.client.get("/api/categories/not-a-uuid/", format="json")

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    # ---- create ----

    def test_create(self):
        """会社とカテゴリ名を指定すると、カテゴリが作成され 201 が返る。"""
        payload = {"company": str(self.company_a.id), "name": "食品"}

        response = self.client.post("/api/categories/", payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Category.objects.count(), 1)
        created = Category.objects.get(pk=response.json()["id"])
        self.assertEqual(created.name, "食品")
        self.assertEqual(created.company, self.company_a)
        self.assertIsNone(created.parent_category)

    def test_create_with_parent_category(self):
        """同じ会社のカテゴリを親として指定して作成できる。"""
        parent = self._create_category(self.company_a, "食品")
        payload = {
            "company": str(self.company_a.id),
            "name": "生鮮食品",
            "parent_category": str(parent.id),
        }

        response = self.client.post("/api/categories/", payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        created = Category.objects.get(pk=response.json()["id"])
        self.assertEqual(created.parent_category, parent)

    def test_create_returns_400_when_company_missing(self):
        """会社を指定しない場合、400 が返り作成されない。"""
        response = self.client.post("/api/categories/", {"name": "食品"}, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("company", response.json())
        self.assertEqual(Category.objects.count(), 0)

    def test_create_returns_400_when_name_missing(self):
        """カテゴリ名を指定しない場合、400 が返り作成されない。"""
        payload = {"company": str(self.company_a.id)}

        response = self.client.post("/api/categories/", payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("name", response.json())
        self.assertEqual(Category.objects.count(), 0)

    def test_create_returns_400_when_name_is_blank(self):
        """カテゴリ名が空文字の場合、400 が返る。"""
        payload = {"company": str(self.company_a.id), "name": ""}

        response = self.client.post("/api/categories/", payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("name", response.json())

    def test_create_returns_400_when_name_exceeds_max_length(self):
        """カテゴリ名が 255 文字を超える場合、400 が返る。"""
        payload = {"company": str(self.company_a.id), "name": "あ" * 256}

        response = self.client.post("/api/categories/", payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("name", response.json())

    def test_create_returns_400_when_company_does_not_exist(self):
        """存在しない会社 ID を指定すると 400 が返る。"""
        payload = {"company": str(uuid.uuid4()), "name": "食品"}

        response = self.client.post("/api/categories/", payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("company", response.json())

    def test_create_returns_400_for_duplicate_name_in_same_company(self):
        """同じ会社に同名カテゴリが既にある場合、500 ではなく 400 が返る。"""
        self._create_category(self.company_a, "食品")
        payload = {"company": str(self.company_a.id), "name": "食品"}

        response = self.client.post("/api/categories/", payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("name", response.json())
        self.assertEqual(Category.objects.count(), 1)

    def test_create_allows_same_name_for_different_companies(self):
        """別会社であれば同名カテゴリを作成できる。"""
        self._create_category(self.company_a, "食品")
        payload = {"company": str(self.company_b.id), "name": "食品"}

        response = self.client.post("/api/categories/", payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Category.objects.count(), 2)

    def test_create_returns_400_when_parent_belongs_to_other_company(self):
        """他社のカテゴリを親に指定すると 400 が返る。"""
        other_parent = self._create_category(self.company_b, "書籍")
        payload = {
            "company": str(self.company_a.id),
            "name": "食品",
            "parent_category": str(other_parent.id),
        }

        response = self.client.post("/api/categories/", payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("parent_category", response.json())

    def test_create_with_explicit_null_parent_category(self):
        """parent_category に null を明示しても作成できる。"""
        payload = {
            "company": str(self.company_a.id),
            "name": "食品",
            "parent_category": None,
        }

        response = self.client.post("/api/categories/", payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        created = Category.objects.get(pk=response.json()["id"])
        self.assertIsNone(created.parent_category)

    def test_create_returns_400_when_parent_does_not_exist(self):
        """存在しない親カテゴリ ID を指定すると 400 が返る。"""
        payload = {
            "company": str(self.company_a.id),
            "name": "食品",
            "parent_category": str(uuid.uuid4()),
        }

        response = self.client.post("/api/categories/", payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("parent_category", response.json())

    def test_create_returns_400_for_malformed_company_id(self):
        """UUID 形式でない company を指定すると 400 が返る。"""
        payload = {"company": "not-a-uuid", "name": "食品"}

        response = self.client.post("/api/categories/", payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("company", response.json())

    def test_create_ignores_read_only_fields(self):
        """id・created_at・updated_at を指定しても無視され、サーバー側の値が使われる。"""
        forced_id = str(uuid.uuid4())
        payload = {
            "company": str(self.company_a.id),
            "name": "食品",
            "id": forced_id,
            "created_at": "2000-01-01T00:00:00Z",
            "updated_at": "2000-01-01T00:00:00Z",
        }

        response = self.client.post("/api/categories/", payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        body = response.json()
        self.assertNotEqual(body["id"], forced_id)
        self.assertNotEqual(body["created_at"], "2000-01-01T00:00:00Z")
        self.assertNotEqual(body["updated_at"], "2000-01-01T00:00:00Z")

    def test_create_returns_400_when_duplicate_slips_past_validation(self):
        """事前検証をすり抜けた重複でも、DB 制約違反は 500 ではなく 400 に変換される。"""
        self._create_category(self.company_a, "食品")
        payload = {"company": str(self.company_a.id), "name": "食品"}

        # 同時リクエストで「検証通過後に同名が commit される」競合を、検証の素通しで再現する
        with mock.patch.object(CategorySerializer, "validate", side_effect=lambda attrs: attrs):
            response = self.client.post("/api/categories/", payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(Category.objects.count(), 1)

    # ---- update ----

    def test_update(self):
        """PUT でカテゴリ名を変更できる。"""
        category = self._create_category(self.company_a, "食品")
        payload = {"company": str(self.company_a.id), "name": "飲料"}

        response = self.client.put(f"/api/categories/{category.id}/", payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        category.refresh_from_db()
        self.assertEqual(category.name, "飲料")

    def test_partial_update(self):
        """PATCH でカテゴリ名のみを変更でき、親カテゴリは維持される。"""
        parent = self._create_category(self.company_a, "食品")
        child = self._create_category(self.company_a, "生鮮食品", parent=parent)

        response = self.client.patch(f"/api/categories/{child.id}/", {"name": "冷凍食品"}, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        child.refresh_from_db()
        self.assertEqual(child.name, "冷凍食品")
        self.assertEqual(child.parent_category, parent)

    def test_partial_update_can_clear_parent_category(self):
        """PATCH で親カテゴリを null に戻せる。"""
        parent = self._create_category(self.company_a, "食品")
        child = self._create_category(self.company_a, "生鮮食品", parent=parent)

        response = self.client.patch(f"/api/categories/{child.id}/", {"parent_category": None}, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        child.refresh_from_db()
        self.assertIsNone(child.parent_category)

    def test_update_keeps_parent_when_parent_category_omitted(self):
        """PUT で parent_category を省略した場合、既存の親カテゴリは維持される。"""
        parent = self._create_category(self.company_a, "食品")
        child = self._create_category(self.company_a, "生鮮食品", parent=parent)
        payload = {"company": str(self.company_a.id), "name": "冷凍食品"}

        response = self.client.put(f"/api/categories/{child.id}/", payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        child.refresh_from_db()
        self.assertEqual(child.name, "冷凍食品")
        self.assertEqual(child.parent_category, parent)

    def test_update_returns_400_when_company_missing_on_put(self):
        """PUT で company を省略すると 400 が返る。"""
        category = self._create_category(self.company_a, "食品")

        response = self.client.put(f"/api/categories/{category.id}/", {"name": "飲料"}, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("company", response.json())

    def test_update_allows_keeping_own_name(self):
        """名前を変えない PUT は、自分自身と重複扱いにならず成功する。"""
        category = self._create_category(self.company_a, "食品")
        payload = {"company": str(self.company_a.id), "name": "食品"}

        response = self.client.put(f"/api/categories/{category.id}/", payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_update_returns_400_for_duplicate_name_in_same_company(self):
        """同じ会社の既存カテゴリと同名への変更は 400 が返る。"""
        self._create_category(self.company_a, "食品")
        category = self._create_category(self.company_a, "書籍")

        response = self.client.patch(f"/api/categories/{category.id}/", {"name": "食品"}, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("name", response.json())
        category.refresh_from_db()
        self.assertEqual(category.name, "書籍")

    def test_update_returns_400_when_company_changed(self):
        """カテゴリの所属会社は変更できず、400 が返る。"""
        category = self._create_category(self.company_a, "食品")
        payload = {"company": str(self.company_b.id), "name": "食品"}

        response = self.client.put(f"/api/categories/{category.id}/", payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("company", response.json())
        category.refresh_from_db()
        self.assertEqual(category.company, self.company_a)

    def test_update_returns_400_when_parent_is_self(self):
        """自分自身を親に指定すると 400 が返る。"""
        category = self._create_category(self.company_a, "食品")

        response = self.client.patch(
            f"/api/categories/{category.id}/",
            {"parent_category": str(category.id)},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("parent_category", response.json())

    def test_update_returns_400_when_parent_creates_cycle(self):
        """子孫を親に指定して循環が生じる場合、400 が返る。"""
        grandparent = self._create_category(self.company_a, "食品")
        parent = self._create_category(self.company_a, "生鮮食品", parent=grandparent)
        child = self._create_category(self.company_a, "鮮魚", parent=parent)

        response = self.client.patch(
            f"/api/categories/{grandparent.id}/",
            {"parent_category": str(child.id)},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("parent_category", response.json())
        grandparent.refresh_from_db()
        self.assertIsNone(grandparent.parent_category)

    def test_update_returns_404_for_unknown_id(self):
        """存在しない ID への PUT は 404 が返る。"""
        payload = {"company": str(self.company_a.id), "name": "食品"}

        response = self.client.put(f"/api/categories/{uuid.uuid4()}/", payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    # ---- destroy ----

    def test_destroy(self):
        """DELETE でカテゴリが削除され 204 が返る。"""
        category = self._create_category(self.company_a, "食品")

        response = self.client.delete(f"/api/categories/{category.id}/", format="json")

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Category.objects.filter(pk=category.id).exists())

    def test_destroy_returns_404_for_unknown_id(self):
        """存在しない ID への DELETE は 404 が返る。"""
        response = self.client.delete(f"/api/categories/{uuid.uuid4()}/", format="json")

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_destroy_parent_sets_child_parent_to_null(self):
        """親カテゴリを削除すると、子カテゴリの親は null になり子自体は残る。"""
        parent = self._create_category(self.company_a, "食品")
        child = self._create_category(self.company_a, "生鮮食品", parent=parent)

        response = self.client.delete(f"/api/categories/{parent.id}/", format="json")

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        child.refresh_from_db()
        self.assertIsNone(child.parent_category)
