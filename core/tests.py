import pytest
from lark import LarkError

from .models import *

# Create your tests here.
from .templatetags.greaterthan import gt


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
