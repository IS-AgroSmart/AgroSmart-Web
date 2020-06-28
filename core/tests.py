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
        assert parser.make_string("nir**2") == "asarray(D, dtype=float32)**2.0"

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

    def test_unary_minus(self, parser):
        assert parser.make_string("-red") == "-1.0*asarray(C, dtype=float32)"

    def test_is_valid(self, parser):
        assert parser.is_valid("blue")
        assert parser.is_valid("-blue")
        assert not parser.is_valid("blue+")

    def test_unary_minus_complex(self, parser):
        assert parser.make_string("blue/(-red)") == "asarray(A, dtype=float32)/(-1.0*asarray(C, dtype=float32))"


class TestGreaterThanTemplateTag:
    def test_tag(self):
        assert not gt(1, 2)
        assert not gt(0, 1)
        assert gt(2, -1)


class TestCameraNameTemplateTag:
    def test_tag(self):
        from .templatetags.reporttags import cameraname
        assert cameraname("REDEDGE") == "Micasense RedEdge"
        assert cameraname("RGB") == "Cámara RGB"
        assert "Cámara no reconocida" in cameraname("FOOBAR") and "FOOBAR" in cameraname("FOOBAR")


class TestStateNameTemplateTag:
    def test_tag(self):
        from .templatetags.reporttags import statename
        assert statename("COMPLETE") == "Completado con éxito"
        assert statename("ERROR") == "Completado con errores"
        assert statename("CANCELED") == "Cancelado por el usuario"
        assert "Estado no reconocido" in statename("FOOBAR") and "FOOBAR" in statename("FOOBAR")


class TestMillisToStringTemplateTag:
    def test_tag(self):
        from .templatetags.reporttags import millistostring
        assert millistostring(1000) == "0 h, 0 min, 1 s"
        assert millistostring(1000 * 60) == "0 h, 1 min, 0 s"
