import uuid

from rest_framework import status
from rest_framework.test import APITestCase

from api.models import Category, Company


class CompanyViewTests(APITestCase):
    def test_list(self):
        """登録済みの会社が全件返る。"""
        company_a = Company.objects.create(name="Company A")
        company_b = Company.objects.create(name="Company B")

        response = self.client.get("/api/companies/", format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # モデルに既定の並び順が無いため、順序には依存せず集合で検証する
        self.assertEqual(
            {item["id"] for item in response.json()},
            {str(company_a.id), str(company_b.id)},
        )

    def test_retrieve(self):
        """会社の詳細が、定義したフィールドすべてを含んで返る。"""
        company = Company.objects.create(name="Company A")

        response = self.client.get(f"/api/companies/{company.id}/", format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        body = response.json()
        self.assertEqual(body["id"], str(company.id))
        self.assertEqual(body["name"], "Company A")
        self.assertIsNotNone(body["created_at"])
        self.assertIsNotNone(body["updated_at"])

    def test_list_returns_empty_list_when_no_companies(self):
        """会社が存在しない場合、空のリストが返る。"""
        response = self.client.get("/api/companies/", format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json(), [])

    def test_retrieve_returns_404_for_unknown_id(self):
        """存在しない ID を指定すると 404 が返る。"""
        response = self.client.get(f"/api/companies/{uuid.uuid4()}/", format="json")

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_create(self):
        """会社名を指定すると、会社が作成され 201 が返る。"""
        response = self.client.post("/api/companies/", {"name": "Company A"}, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Company.objects.count(), 1)
        created = Company.objects.get(pk=response.json()["id"])
        self.assertEqual(created.name, "Company A")

    def test_create_returns_400_when_name_missing(self):
        """会社名を指定しない場合、400 が返り作成されない。"""
        response = self.client.post("/api/companies/", {}, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("name", response.json())
        self.assertEqual(Company.objects.count(), 0)

    def test_create_returns_400_when_name_is_blank(self):
        """会社名が空文字の場合、400 が返る。"""
        response = self.client.post("/api/companies/", {"name": ""}, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("name", response.json())

    def test_create_returns_400_when_name_exceeds_max_length(self):
        """会社名が 255 文字を超える場合、400 が返る。"""
        response = self.client.post("/api/companies/", {"name": "あ" * 256}, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("name", response.json())

    def test_update(self):
        """PUT で会社名を変更できる。"""
        company = Company.objects.create(name="Company A")

        response = self.client.put(f"/api/companies/{company.id}/", {"name": "Company A2"}, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        company.refresh_from_db()
        self.assertEqual(company.name, "Company A2")

    def test_partial_update(self):
        """PATCH で会社名を変更できる。"""
        company = Company.objects.create(name="Company A")

        response = self.client.patch(f"/api/companies/{company.id}/", {"name": "Company A2"}, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        company.refresh_from_db()
        self.assertEqual(company.name, "Company A2")

    def test_update_returns_404_for_unknown_id(self):
        """存在しない ID への PUT は 404 が返る。"""
        response = self.client.put(f"/api/companies/{uuid.uuid4()}/", {"name": "Company A"}, format="json")

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_destroy_returns_404_for_unknown_id(self):
        """存在しない ID への DELETE は 404 が返る。"""
        response = self.client.delete(f"/api/companies/{uuid.uuid4()}/", format="json")

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_destroy(self):
        """DELETE で会社が削除され 204 が返る。"""
        company = Company.objects.create(name="Company A")

        response = self.client.delete(f"/api/companies/{company.id}/", format="json")

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Company.objects.filter(pk=company.id).exists())

    def test_destroy_cascades_categories(self):
        """会社を削除すると、その会社のカテゴリも削除される。"""
        company = Company.objects.create(name="Company A")
        Category.objects.create(company=company, name="食品")

        response = self.client.delete(f"/api/companies/{company.id}/", format="json")

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(Category.objects.count(), 0)
