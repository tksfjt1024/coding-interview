from django.test import SimpleTestCase

from api.models import Category, Company


class CompanyModelTests(SimpleTestCase):
    def test_str_returns_name(self):
        """str() は会社名を返す。"""
        company = Company(name="Company A")

        self.assertEqual(str(company), "Company A")


class CategoryModelTests(SimpleTestCase):
    def test_str_returns_name(self):
        """str() はカテゴリ名を返す。"""
        category = Category(name="食品")

        self.assertEqual(str(category), "食品")
