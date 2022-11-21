# Copyright (c) 2019-2021 Thomas Kramer.
# SPDX-FileCopyrightText: 2022 Thomas Kramer
#
# SPDX-License-Identifier: GPL-3.0-or-later

from lark import Lark, Transformer, v_args
from .types import *

liberty_grammar = r'''
    ?start: file
    
    file: group*
    
    group: name argument_list group_body
    group_body: "{" (statement)* "}"
    
    argument_list: "(" [value ("," value)*] ")"
    
    ?statement: attribute
        | group
        | define
        
    ?value: name
        | versionstring
        | number
        | NUMBER_WITH_UNIT -> number_with_unit
        | numbers
        | string -> escaped_string
        | name_bit_selection
        | arithmetic_expression
        
    ?arith_op: "*" -> op_mul | "+" -> op_add | "-" -> op_sub | "/" -> op_div
    arithmetic_expression: (("-" name | name | number) (arith_op (name | number))+ ) | ("!" name)
        
    numbers: "\"" [number ("," number)*] "\""
        
    unit: NAME
        
    ?attribute: simple_attribute
        | complex_attribute
        
    simple_attribute: name ":" value ";"?
    
    complex_attribute: name argument_list ";"?
    
    define_argument: string | name
    define: "define" "(" define_argument "," define_argument "," define_argument ")" ";"?

    ?versionstring: number number
    
    NAME : ("_"|LETTER) ("_"|"."|"!"|LETTER|DIGIT)*
    name : NAME
    string: ESCAPED_STRING_MULTILINE
        | ("_"|LETTER) ("_"|"."|"-"|","|":"|"!"|LETTER|DIGIT)*
    
    number: SIGNED_NUMBER
    // The unit cannot be "e" or "E" because it is used as floating-point notation.
    NUMBER_WITH_UNIT: SIGNED_NUMBER ( ("a".."d" | "f".."z" | "A".."D" | "F".."Z") | (LETTER LETTER+) )

    name_bit_selection:  name "[" number [":"] [number] "]"

    COMMENT: /\/\*(\*(?!\/)|[^*])*\*\//
    NEWLINE: /\\?\r?\n/
    
    _STRING_INNER: /.*?/
    _STRING_ESC_INNER_MULTILINE: (_STRING_INNER | NEWLINE)+ /(?<!\\)(\\\\)*?/ 
    
    ESCAPED_STRING_MULTILINE : "\"" _STRING_ESC_INNER_MULTILINE "\""
    
    %import common.WORD
    %import common.ESCAPED_STRING
    %import common.DIGIT
    %import common.LETTER
    
    %import common.SIGNED_NUMBER
    %import common.WS
    
    %ignore WS
    %ignore COMMENT
    %ignore NEWLINE
'''


@v_args(inline=True)
class LibertyTransformer(Transformer):

    def file(self, *groups):
        return list(groups)

    def escaped_string(self, s):
        s = s[1:-1].replace('\\"', '"')
        s = s.replace('\\\n', '')
        return EscapedString(s)

    def string(self, s):
        return s[:]

    def name(self, s):
        return s[:]

    def number(self, s):
        return float(s)

    def op_add(self):
        return "+"

    def op_sub(self):
        return "-"

    def op_mul(self):
        return "*"

    def op_div(self):
        return "/"

    def arithmetic_expression(self, *s):
        expr_string = " ".join((f"{x}" for x in s))
        return ArithExpression(expr_string)

    unit = string
    value = string

    def group_body(self, *args):
        return list(args)

    def number_with_unit(self, num_unit):
        assert isinstance(num_unit, str)
        unit_len = 0
        for c in reversed(num_unit):
            if not str(c).isalpha():
                break
            unit_len += 1
        unit = num_unit[-unit_len:]
        num = float(num_unit[:-unit_len])
        return WithUnit(num, unit)

    def simple_attribute(self, name, value):
        return Attribute(name, value)

    def complex_attribute(self, name, arg_list):
        return Attribute(name, arg_list)

    def define_argument(self, arg) -> str:
        if isinstance(arg, str):
            # Strip quote chars.
            if arg.startswith('"') and arg.endswith('"'):
                return arg[1:-1]
            else:
                return arg
        else:
            return arg

    def define(self, attribute_name, group_name, attribute_type) -> Define:
        """

        :param attribute_name:
        :param group_name:
        :param attribute_type: boolean, string, integer or float
        :return:
        """
        return Define(attribute_name, group_name, attribute_type)

        # @v_args(inline=True)
        # def value(self, value):
        #     return value

    def argument_list(self, *args):
        return list(args)

    def group(self, group_name, group_args, body):
        attrs = []
        sub_groups = []
        defines = []
        for a in body:
            if isinstance(a, Attribute):
                attrs.append(a)
            elif isinstance(a, Group):
                sub_groups.append(a)
            elif isinstance(a, Define):
                defines.append(a)
            else:
                assert False, "Unexpected object type: {}".format(type(a))

        return Group(group_name, group_args, attrs, sub_groups, defines)

    def name_bit_selection(self, *args):
        return NameBitSelection(*args)


def parse_liberty(data: str) -> Group:
    """
    Parse a string containing data of a liberty file.
    The liberty string must contain exactly one top library. If more than one top
    should be supported then `parse_multi_liberty()` should be used instead.

    :param data: Raw liberty string.
    :return: `Group` object of library.
    """
    top_groups = parse_multi_liberty(data)

    if len(top_groups) == 1:
        return top_groups[0]
    else:
        raise Exception("Liberty does not contain exactly one top group. Use `parse_multi_liberty()` instead.")


def parse_multi_liberty(data: str) -> List[Group]:
    """
    Parse a string containing data of a liberty file.
    The liberty file may contain many top-level libraries.
    :param data: Raw liberty string.
    :return: List of `Group` objects.
    """
    liberty_parser = Lark(liberty_grammar,
                          parser='lalr',
                          #lexer='basic',
                          transformer=LibertyTransformer()
                          )
    library = liberty_parser.parse(data)
    return library


def test_parse_liberty_simple():
    data = r"""
library(test) { 
  time_unit: 1ns;
  string: "asdf";
  mygroup(a, b) {}
  empty() {}
  somegroup(a, b, c) {
    nested_group(d, e) {
        simpleattr_float: 1.2;
    }
  }
  simpleattr_int : 1;
  complexattr(a, b);
  define(myNewAttr, validinthisgroup, float);
  pin(A[25]) {}
  pin(B[32:0]) {}
}
"""
    library = parse_liberty(data)
    assert isinstance(library, Group)

    # Check attribute values.
    assert library.get_attribute('simpleattr_int') == 1
    assert library.get_attribute('complexattr') == ['a', 'b']

    # Format, parse, format and check that the result stays the same.
    str1 = str(library)
    library2 = parse_liberty(str1)
    str2 = str(library2)
    assert (str1 == str2)


def test_parse_liberty_with_unit():
    data = r"""
library(test) { 
  time_unit: 1ns ;
}
"""
    library = parse_liberty(data)
    assert isinstance(library, Group)

    # Check values with unit.
    assert isinstance(library.get_attribute('time_unit'), WithUnit)
    assert library.get_attribute('time_unit').value == 1
    assert library.get_attribute('time_unit').unit == 'ns'

    # Format, parse, format and check that the result stays the same.
    str1 = str(library)
    library2 = parse_liberty(str1)
    str2 = str(library2)
    assert (str1 == str2)


def test_parse_liberty_with_multline():
    data = r"""
table(table_name2){ 
    str: "asd\
    f";
    index_1("1, 2, 3, 4, 5, 6, 7, 8"); 
    value("0001, 0002, 0003, 0004, \
    0005, 0006, 0007, 0008");
}
"""
    library = parse_liberty(data)
    assert isinstance(library, Group)

    str1 = str(library)
    library2 = parse_liberty(str1)
    str2 = str(library2)
    assert (str1 == str2)


def test_parse_liberty_statetable_multiline():
    # From https://codeberg.org/tok/liberty-parser/issues/6
    data = r"""
statetable ("CK E SE","IQ") {
	     table : "L L L : - : L ,\
	              L L H : - : H ,\
	              L H L : - : H ,\
	              L H H : - : H ,\
	              H - - : - : N " ;
	}
"""

    library = parse_liberty(data)
    assert isinstance(library, Group)

    str1 = str(library)
    library2 = parse_liberty(str1)
    str2 = str(library2)
    assert (str1 == str2)


def test_parse_liberty_with_define():
    data = r"""
group(test){ 
    define (a, b, c);
    define (x, y, z);
}
"""
    library = parse_liberty(data)
    assert isinstance(library, Group)
    assert isinstance(library.defines[0], Define)
    assert isinstance(library.defines[1], Define)

    str1 = str(library)
    library2 = parse_liberty(str1)
    str2 = str(library2)
    assert (str1 == str2)


def test_parse_liberty_multi_complex_attributes():
    data = r"""
group(test){ 
    define_group(g1, x);
    define_group(g2, z);
    voltage_map(VDD, 1.0);
    voltage_map(VSS, 0.0);
}
"""
    library = parse_liberty(data)
    assert isinstance(library, Group)

    # Check if `voltage_map` is parsed as expected.
    assert library.get_attributes('voltage_map')[0] == ['VDD', 1.0]
    assert library.get_attributes('voltage_map')[1] == ['VSS', 0.0]

    str1 = str(library)
    library2 = parse_liberty(str1)
    assert len(library.attributes) == 4
    str2 = str(library2)
    assert (str1 == str2)


def test_parse_liberty_freepdk():
    import os.path
    lib_file = os.path.join(os.path.dirname(__file__), '../test_data/gscl45nm.lib')

    data = open(lib_file).read()

    library = parse_liberty(data)
    assert isinstance(library, Group)

    library_str = str(library)
    open('/tmp/lib.lib', 'w').write(library_str)
    library2 = parse_liberty(library_str)
    assert isinstance(library2, Group)
    library_str2 = str(library2)
    assert (library_str == library_str2)

    cells = library.get_groups('cell')

    invx1 = library.get_group('cell', 'XOR2X1')
    assert invx1 is not None

    pin_y = invx1.get_group('pin', 'Y')
    timings_y = pin_y.get_groups('timing')
    timing_y_a = [g for g in timings_y if g['related_pin'] == 'A'][0]
    assert timing_y_a['related_pin'] == 'A'

    array = timing_y_a.get_group('cell_rise').get_array('values')
    assert array.shape == (6, 6)


def test_wire_load_model():
    """
    Test that multiple attributes with the same name don't overwrite eachother.
    See: https://codeberg.org/tok/liberty-parser/issues/7
    """

    data = r"""
    wire_load("1K_hvratio_1_4") {
        capacitance : 1.774000e-01;
        resistance : 3.571429e-03;
        slope : 5.000000;
        fanout_length( 1, 1.3207 );
        fanout_length( 2, 2.9813 );
        fanout_length( 3, 5.1135 );
        fanout_length( 4, 7.6639 );
        fanout_length( 5, 10.0334 );
        fanout_length( 6, 12.2296 );
        fanout_length( 8, 19.3185 );
    }
"""
    wire_load = parse_liberty(data)
    fanout_lengths = wire_load.get_attributes("fanout_length")
    assert isinstance(fanout_lengths, list)
    assert len(fanout_lengths) == 7
    expected_fanoutlength = [
        [1, 1.3207],
        [2, 2.9813],
        [3, 5.1135],
        [4, 7.6639],
        [5, 10.0334],
        [6, 12.2296],
        [8, 19.3185],
    ]
    assert fanout_lengths == expected_fanoutlength


def test_argument_with_dot():
    """
    Parse names with dots like `a.b`.
    """
    # Issue #10
    data = r"""
operating_conditions(ff28_1.05V_0.00V_0.00V_0.00V_125C_7y50kR){
}    
"""
    group = parse_liberty(data)

    assert group.args == ["ff28_1.05V_0.00V_0.00V_0.00V_125C_7y50kR"]


def test_complex_attribute_without_semicolon():
    """
    Parse complex attributes without trailing `;`.
    """
    # Issue #10
    data = r"""
library(){
    cplxAttr1(1)
    cplxAttr2(1, 2)
    cplxAttr3(3);
    cplxAttr4(4)
}
"""
    group = parse_liberty(data)

    assert len(group.attributes) == 4


def test_simple_attribute_without_semicolon():
    """
    Parse simple attributes without trailing `;`.
    """
    # Issue #10
    data = r"""
library(){
    simpleAttr1: 1ps
    simpleAttr2: 2;
    simpleAttr3: 3
}
"""
    group = parse_liberty(data)

    assert len(group.attributes) == 3


def test_multi_top_level_libraries():
    """
    Parse files with more than one top-level library.
    """
    # Issue #10
    data = r"""
library(lib1){
}
library(lib2){
}
"""
    tops = parse_multi_liberty(data)
    assert isinstance(tops, list)
    assert len(tops) == 2


def test_define():
    # Issue #10
    data = r"""
    library(){
        define ("a", "b", "c");
        define (d, "e", f);
        define (g, h, i)
    }
    """
    group = parse_liberty(data)
    assert isinstance(group, Group)
    assert len(group.defines) == 3

    assert group.defines[0].attribute_name == "a"
    assert group.defines[0].group_name == "b"
    assert group.defines[0].attribute_type == "c"
    assert group.defines[1].attribute_name == "d"
    assert group.defines[1].group_name == "e"
    assert group.defines[1].attribute_type == "f"
    assert group.defines[2].attribute_name == "g"
    assert group.defines[2].group_name == "h"
    assert group.defines[2].attribute_type == "i"


def test_arithmetic_expressions():
    # Issue 10

    data = r"""
    input_voltage(cmos) {
        vil : 0.5 * VDD ;
        vih : 0.7 * VDD ;
        vimin : -0.5 ;
        vimax : VDD * 1.1 + 0.5 ;
    }
"""
    group = parse_liberty(data)
    assert isinstance(group, Group)
    assert len(group.attributes) == 4

    for attr in group.attributes:
        expr_str = attr.value
        if not isinstance(attr.value, float):
            assert isinstance(expr_str, ArithExpression)

            expr = expr_str.to_sympy_expression()
            print(expr)

    assert group.attributes[3].value.to_sympy_expression() == sympy.parse_expr("VDD * 1.1 + 0.5")

def test_single_letter_units():
    # Issue 11

    data = r"""
    test() {
        int_value : 1V ; 
        float_value : 2.5e-1A ;
    }
"""

    group = parse_liberty(data)
    assert isinstance(group, Group)
    assert len(group.attributes) == 2
    assert group.attributes[0].value == WithUnit(1, "V")
    assert group.attributes[1].value == WithUnit(0.25, "A")

def test_units_starting_with_E():
    # Issue 11

    data = r"""
    test() {
        int_value : 1eV ; 
        float_value : 2.5e-1EV ;
    }
"""

    group = parse_liberty(data)
    assert isinstance(group, Group)
    assert len(group.attributes) == 2
    assert group.attributes[0].value == WithUnit(1, "eV")
    assert group.attributes[1].value == WithUnit(0.25, "EV")
