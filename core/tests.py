import signal
from datetime import datetime

from django.contrib.auth import get_user_model
from django.db import IntegrityError
from django.test import TestCase
from .models import *


# Create your tests here.
class FlightModelTest(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user('temporary', 'temporary@gmail.com', 'temporary')
        self.user2 = User.objects.create_user('temporary2', 'temporary2@gmail.com', 'temporary')

        post_save.disconnect(create_nodeodm_task, sender=Flight)
        post_save.disconnect(link_demo_flight_to_active_users, sender=Flight)
        post_delete.disconnect(delete_nodeodm_task, sender=Flight)
        post_delete.disconnect(delete_thumbnail, sender=Flight)
        post_delete.disconnect(delete_geoserver_workspace, sender=Flight)

    def test_cannot_repeat_flight_name_on_same_user(self):
        self.user.flight_set.create(name="title", date=datetime.now())
        self.assertRaises(IntegrityError, self.user.flight_set.create, name="title", date=datetime.now())

    def test_can_repeat_flight_name_on_different_user(self):
        self.user.flight_set.create(name="title", date=datetime.now())
        try:
            self.user2.flight_set.create(name="title", date=datetime.now())
        except IntegrityError:
            self.fail("Attempt to create flight raised IntegrityError unexpectedly!")