from django.test import TestCase
from django.urls import resolve


class FormationUrlTests(TestCase):
    def test_my_courses_route_resolves_to_my_courses_view(self):
        match = resolve("/formation/my-courses/")

        self.assertEqual(match.view_name, "formation:my_courses")
        self.assertEqual(match.kwargs, {})
