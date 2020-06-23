import pytest
from django.contrib.auth import get_user_model

from core.models import UserProject
from core.test_viewsets import FlightsMixin


class BaseModelTest:
    @pytest.fixture
    def users(self):
        User = get_user_model()
        u1 = User.objects.create(username='temporary', email='temporary@gmail.com', password='temporary')
        u2 = User.objects.create(username='temporary2', email='temporary2@gmail.com', password='temporary2')
        admin = User.objects.create(username='admin', email='admin@gmail.com', password='admin', is_staff=True)
        return u1, u2, admin


@pytest.mark.django_db
class TestUserProjectModel(FlightsMixin, BaseModelTest):
    @pytest.fixture
    def projects(self, users):
        p1 = users[0].user_projects.create(name="proj1")
        p2 = users[0].user_projects.create(name="proj2")
        return p1, p2

    def test_disk_path(self, users, projects):
        assert projects[1].get_disk_path() == "/projects/" + str(projects[1].uuid)

    def test_all_flights_multispectral(self, users, projects, flights):
        projects[0].flights.add(flights[0], flights[1])
        assert projects[0].all_flights_multispectral()
        projects[1].flights.add(flights[0], flights[1], flights[2])
        assert not projects[1].all_flights_multispectral()
