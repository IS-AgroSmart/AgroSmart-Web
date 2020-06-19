import signal
from datetime import datetime

import pytest
from django.contrib.auth import get_user_model
from django.db import IntegrityError
from django.test import TestCase
from lark import LarkError

from .models import *

# Create your tests here.
from .templatetags.greaterthan import gt


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
        post_delete.disconnect(delete_geoserver_workspace, sender=UserProject)
        post_delete.disconnect(delete_on_disk, sender=UserProject)

    def test_cannot_repeat_flight_name_on_same_user(self):
        self.user.flight_set.create(name="title", date=datetime.now())
        self.assertRaises(IntegrityError, self.user.flight_set.create, name="title", date=datetime.now())

    def test_can_repeat_flight_name_on_different_user(self):
        self.user.flight_set.create(name="title", date=datetime.now())
        try:
            self.user2.flight_set.create(name="title", date=datetime.now())
        except IntegrityError:
            self.fail("Attempt to create flight raised IntegrityError unexpectedly!")

    def test_flight_initializes_as_waiting_for_images(self):
        f = self.user.flight_set.create(name="flight", date=datetime.now())
        self.assertEqual(f.state, FlightState.WAITING.name)


class TestParser:
    @pytest.fixture
    def parser(self):
        return FormulaParser()

    def test_simple(self, parser):
        assert parser.make_string("blue+red") == "asarray(A, dtype=float32)+asarray(C, dtype=float32)"

    def test_parens(self, parser):
        assert parser.make_string("((green+nir))") == "((asarray(B, dtype=float32)+asarray(D, dtype=float32)))"

    def test_complex(self, parser):
        assert parser.make_string("((nir-red)/(nir+red))") == \
               "((asarray(D, dtype=float32)-asarray(C, dtype=float32))/" \
               "(asarray(D, dtype=float32)+asarray(C, dtype=float32)))"

    def test_float_conversion(self, parser):
        assert parser.make_string("nir+1") == "asarray(D, dtype=float32)+1.0"

    def test_spaces_ignored(self, parser):
        assert parser.make_string("red +    green") == "asarray(C, dtype=float32)+asarray(B, dtype=float32)"

    def test_unknown_channel(self, parser):
        with pytest.raises(LarkError):
            parser.make_string("blue+foobar")

    def test_unbalanced_parens(self, parser):
        with pytest.raises(LarkError):
            parser.make_string("((blue+nir)")

    def test_unknown_operator(self, parser):
        with pytest.raises(LarkError):
            parser.make_string("red?1")

    def test_wrong_parens_close(self, parser):
        with pytest.raises(LarkError):
            parser.make_string("((blue+)nir)")


class TestGreaterThanTemplateTag:
    def test_tag(self):
        assert not gt(1, 2)
        assert not gt(0, 1)
        assert gt(2, -1)
