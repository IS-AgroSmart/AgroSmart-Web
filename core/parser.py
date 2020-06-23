from lark import Lark, Transformer, LarkError


class FormulaParser:
    grammar = """start: term (FACTOR_OP term)*
term: factor (TERM_OP factor)*
factor: (FACTOR_OP factor) -> plusminus
      | atom 
      | power
power: atom "**" factor
atom: ("(" start ")") -> parens
    | NAME | NUMBER
NAME: "blue" | "green" | "red" | "nir" | "rdedge"
FACTOR_OP: "+" | "-"
TERM_OP: "*" | "/"

%import common.NUMBER
%import common.WS
%ignore WS
    """

    def __init__(self):
        self.parser = Lark(self.grammar)

    def _parse(self, formula):
        return self.parser.parse(formula)

    def is_valid(self, formula):
        try:
            self._parse(formula)
            return True
        except LarkError:
            return False

    def make_string(self, formula):
        return FormulaTransformer().transform(self._parse(formula))

    def generate_gdal_calc_command(self, formula: str, index_name: str):
        return 'gdal_calc.py -A odm_orthophoto.tif --A_band=1 -B odm_orthophoto.tif --B_band=2 ' \
               '-C odm_orthophoto.tif --C_band=3 -D odm_orthophoto.tif --D_band=4 -E odm_orthophoto.tif --E_band=5 ' \
               '--calc="{}" ' \
               '--outfile={}.tif --type=Byte --co="TILED=YES" --overwrite --NoDataValue=0'.format(
                self.make_string(formula), index_name)


class FormulaTransformer(Transformer):
    LAYER_TO_INDEX = {"blue": "A", "green": "B", "red": "C", "nir": "D", "rdedge": "E"}

    def start(self, items):
        if len(items) == 1:
            return items[0]
        return items[0] + str(items[1]) + items[2]

    def term(self, items):
        if len(items) == 1:
            return items[0]
        return items[0] + str(items[1]) + items[2]

    def plusminus(self, items):
        return items[1] if items[0] == "+" else "-1.0*" + items[1]

    def factor(self, items):
        return items[0]

    def power(self, items):
        return items[0] + "**" + items[1]

    def parens(self, items):
        return "(" + items[0] + ")"

    def atom(self, items):
        return items[0]

    def NAME(self, name):
        return "asarray({}, dtype=float32)".format(self.LAYER_TO_INDEX[name])

    def NUMBER(self, number):
        return str(float(number))
