# Copyright (c) 2019-2021 Thomas Kramer.
# SPDX-FileCopyrightText: 2022 Thomas Kramer
#
# SPDX-License-Identifier: GPL-3.0-or-later

from typing import Any, List, Dict, Optional, Tuple
from itertools import chain
from .boolean_functions import parse_boolean_function, format_boolean_function
from .arrays import strings_to_array, array_to_strings
import numpy as np
from sympy.logic import boolalg
import sympy


class Define:
    def __init__(self, attribute_name, group_name, attribute_type):
        """

        :param attribute_name: Name of the new defined attribute.
        :param group_name: Name of the group in which the attribute is created.
        :param attribute_type: Data type of the attribute: boolean, string, integer or float
        """

        self.attribute_name = attribute_name
        self.group_name = group_name
        self.attribute_type = attribute_type

    def __str__(self):
        return 'define ("{}", "{}", "{}")'.format(self.attribute_name, self.group_name, self.attribute_type)

    def __repr__(self):
        return str(self)


class Attribute:
    def __init__(self, attribute_name: str, value):
        """
        :param attribute_name: Name of the attribute.
        :param value: Value of the attribute.
        An attribute value can have types
        `float`, `string`, `EscapedString`, `ArithExpression`, `WithUnit`, `NameBitSelection`, `List[float]`.
        """

        self.name = attribute_name
        self.value = value

    def __str__(self):
        return '{}: {}'.format(self.name, self.value)

    def __repr__(self):
        return str(self)


class Group:
    def __init__(self, group_name: str,
                 args: List[str] = None,
                 attributes: List[Attribute] = None,
                 groups: List = None,
                 defines: List[Define] = None):
        self.groups: List[Group] = groups if groups is not None else []

        self.group_name = group_name
        self.args = args if args is not None else []
        assert isinstance(self.args, list)

        self.attributes = attributes if attributes is not None else list()
        assert isinstance(self.attributes, list)
        assert all((isinstance(v, Attribute) for v in self.attributes))

        self.groups = groups if groups is not None else []
        assert isinstance(self.groups, list)
        assert all((isinstance(v, Group) for v in self.groups))

        self.defines: List[Define] = defines if defines is not None else []
        assert isinstance(self.defines, list)
        assert all((isinstance(v, Define) for v in self.defines))

    def get_groups(self, type_name: str, argument: Optional[str] = None) -> List:
        """ Get all groups of type `type_name`.
        Optionally filter the groups by their first argument.
        :param type_name:
        :param argument:
        :return: List[Group]
        """
        return [g for g in self.groups
                if g.group_name == type_name
                and (argument is None or
                     (len(g.args) > 0 and g.args[0] == argument)
                     )
                ]

    def get_group(self, type_name: str, argument: Optional[str] = None):
        """
        Get exactly one group of type `type_name`.
        :param type_name:
        :return: Group
        """
        groups = self.get_groups(type_name, argument=argument)
        assert len(groups) == 1, "There must be exactly one instance of group '{}'. " \
                                 "Found {}.".format(type_name, len(groups))
        return groups[0]

    def __repr__(self) -> str:
        return "%s (%s) t{%s, %s}" % (self.group_name, self.args, self.attributes, self.groups)

    def __str__(self) -> str:
        """
        Create formatted string representation that can be dumped to a liberty file.
        :return:
        """
        return "\n".join(self._format())

    def _format(self, indent: str = " " * 2) -> List[str]:
        """
        Create the liberty file format line by line.
        :return: A list of lines.
        """

        def format_value(v) -> str:
            return str(v)

        define_lines = list()
        for d in self.defines:
            define_lines.append('{};'.format(d))

        sub_group_lines = [g._format(indent=indent) for g in self.groups]

        attr_lines = list()

        for attr in self.attributes:
            attr_name, attr_value = attr.name, attr.value
            if isinstance(attr_value, list):
                # Complex attribute
                formatted = [format_value(x) for x in attr_value]

                if any((isinstance(x, EscapedString) for x in attr_value)):
                    attr_lines.append('{} ('.format(attr_name))
                    for i, l in enumerate(formatted):
                        if i < len(formatted) - 1:
                            end = ', \\'
                        else:
                            end = ''
                        attr_lines.append(indent + l + end)
                    attr_lines.append(');')
                else:
                    values = "({})".format(", ".join(formatted))
                    attr_lines.append("{} {};".format(attr_name, values))
            else:
                # Simple attribute
                values = format_value(attr_value)
                attr_lines.append("{}: {};".format(attr_name, values))

        lines = list()
        lines.append("{} ({}) {{".format(self.group_name, ", ".join([format_value(f) for f in self.args])))

        for l in chain(define_lines, attr_lines, *sub_group_lines):
            lines.append(indent + l)

        lines.append("}")

        return lines

    def get_attributes(self, key: str) -> List[Any]:
        """
        Find attributes values by attribute name.
        :param key: The name of the attribute.
        :return: Returns a list of attribute values.
        """
        return [a.value for a in self.attributes if a.name == key]

    def get_attribute(self, key: str, default=None) -> Any:
        """
        Find exactly one attribute value based on its name.
        Raises an exception if there is no or more than one attributes with this name.
        :param key: Name of the attribute.
        :param default: Returns this default value if no attribute with this name is found.
        :return: The attribute value.
        """
        attrs = self.get_attributes(key)

        if len(attrs) == 0:
            return default

        assert len(attrs) == 1, "Expected to find exactly one attribute with name '{}'. " \
                                "Found {}.".format(key, len(attrs))
        return attrs[0]

    def __getitem__(self, item):
        return self.get_attribute(item)

    def __setitem__(self, key, value):
        self.attributes.append(Attribute(key, value))

    def __contains__(self, item):
        return len(self.get_attributes(item)) > 0

    def get(self, key, default=None):
        return self.get_attribute(key, default)

    def get_array(self, key) -> np.ndarray:
        """
        Get a 1D or 2D array as a numpy.ndarray object.
        :param key: Name of the attribute.
        :return: ndarray
        """
        str_array = self[key]
        str_array = [s.value for s in str_array]
        return strings_to_array(str_array)

    def set_array(self, key, value: np.ndarray):
        str_array = array_to_strings(value)
        str_array = [EscapedString(s) for s in str_array]
        self[key] = str_array

    def get_boolean_function(self, key) -> boolalg.Boolean:
        """
        Get parsed boolean expression.
        Intended for getting the value of the `function` attribute of pins.
        :param key:
        :return: Returns none if there is no function defined under this key.
        """

        f_str = self.get(key)
        if f_str is None:
            return None
        f = parse_boolean_function(f_str.value)
        return f

    def set_boolean_function(self, key, boolean: boolalg.Boolean):
        """
        Format the boolean expression and store it as an attribute with name `key`.
        :param key:
        :param boolean: Sympy boolean expression.
        """
        f_str = format_boolean_function(boolean)
        self[key] = '"{}"'.format(f_str)


class CellGroup(Group):

    def __init__(self, cell_name: str, attributes: List[Attribute],
                 sub_groups: List[Group]):
        super().__init__("cell", args=[cell_name], attributes=attributes,
                         groups=sub_groups)
        self.name = cell_name


class WithUnit:
    """
    Store a value with a unit attached.
    """

    def __init__(self, value, unit: str):
        self.value = value
        self.unit = unit

    def __str__(self):
        return "{}{}".format(self.value, self.unit)

    def __repr__(self):
        return str(self)

    def __eq__(self, other):
        if not isinstance(other, WithUnit):
            return False
        else:
            return self.value == other.value and self.unit == other.unit


class EscapedString:

    def __init__(self, value):
        self.value = value

    def __str__(self):
        return '{}'.format(self.value)

    def __repr__(self):
        return str(self)

    def __eq__(self, other):
        if isinstance(other, EscapedString):
            return self.value == other.value
        else:
            return self.value == other


class ArithExpression:
    """
    Arithmetic expression like `(VDD + 0.5) * 1.2`.
    Arithmetic expressions are stored as strings.
    """

    def __init__(self, value: str):
        self.value = value

    def __str__(self):
        return '{}'.format(self.value)

    def __repr__(self):
        return str(self)

    def to_sympy_expression(self) -> sympy.Expr:
        return sympy.parse_expr(self.value)


class NameBitSelection:
    """Name with bit selection (e.g. ADR[32:0])"""

    def __init__(self, name, sel1, sel2=None):
        self.name = name
        self.sel1 = sel1
        self.sel2 = sel2

    def __str__(self):
        if self.sel2 is not None:
            sel = "{}:{}".format(int(self.sel1), int(self.sel2))
        else:
            sel = int(self.sel1)
        return "{}[{}]".format(self.name, sel)

    def __repr__(self):
        return str(self)


def select_cell(library: Group, cell_name: str) -> Optional[Group]:
    """
    Select a cell by name from a library group.
    :param library:
    :param cell_name:
    :return:
    """
    available_cell_names = {g.args[0] for g in library.get_groups('cell')}

    if cell_name in available_cell_names:
        return library.get_group('cell', cell_name)
    else:
        raise KeyError("Cell name must be one of: {}".format(list(sorted(available_cell_names))))


def select_pin(cell: Group, pin_name: str) -> Optional[Group]:
    """
    Select a pin by name from a cell group.
    :param cell:
    :param pin_name:
    :return:
    """
    available_pin_names = {g.args[0] for g in cell.get_groups('pin')}

    if pin_name in available_pin_names:
        return cell.get_group('pin', pin_name)
    else:
        raise KeyError("Pin name must be one of: {}".format(list(sorted(available_pin_names))))


def select_timing_group(pin: Group,
                        related_pin: str,
                        when: Optional[str] = None,
                        timing_type: Optional[str] = None) -> Optional[Group]:
    """
    Select a timing group by name from a pin group.
    :param pin:
    :param related_pin:
    :param when:
    :param timing_type: Select by 'timing_type' attribute.
    :return:
    """
    # Select by 'related_pin'
    timing_groups = [g
                     for g in pin.get_groups('timing')
                     if 'related_pin' in g
                     and g['related_pin'].value == related_pin
                     ]

    if not timing_groups:
        # Notify the user what `related_pin`s could have been chosen.
        raise KeyError(("No timing group found. Related pin name must be one of: {}".
            format(sorted(list({
            g['related_pin'].value
            for g in pin.get_groups('timing')
            if 'related_pin' in g
        })))
        ))

    # Select by `when`.
    if when is not None:
        timing_groups = [g
                         for g in timing_groups
                         if 'when' in g
                         and g['when'].value == when
                         ]
        if not timing_groups:
            # Notify the user what `related_pin`s could have been chosen.
            raise KeyError(("No timing group found. `when` must be one of: {}".
                format(sorted(list({
                g['when'].value
                for g in timing_groups
                if 'when' in g
            })))
            ))

    # Select by timing_type
    if timing_type is not None:
        timing_groups = [g
                         for g in timing_groups
                         if 'timing_type' in g
                         and g['timing_type'].value == timing_type
                         ]
        if not timing_groups:
            # Notify the user what `timing_type`s could have been chosen.
            raise KeyError(("No timing group found. `timing_type` must be one of: {}".
                format(sorted(list({
                g['timing_type'].value
                for g in timing_groups
            })))
            ))

    timing_group = timing_groups[0]
    return timing_group


def select_timing_table(pin: Group,
                        related_pin: str,
                        table_name: str,
                        when: Optional[str] = None,
                        timing_type: Optional[str] = None) -> Optional[Group]:
    """
    Get a timing table by name from a pin group.
    :param pin: The pin group of the output pin.
    :param related_pin: The related input pin name.
    :param table_name: The name of the timing table. ('cell_rise', 'cell_fall', 'rise_transition', ...)
    :param timing_type: Select by 'timing_type' attribute.
    :return:
    """

    # Find timing group.
    timing_group = select_timing_group(pin, related_pin, timing_type=timing_type, when=when)

    available_table_names = {g.group_name for g in timing_group.groups}

    if table_name in available_table_names:
        return timing_group.get_group(table_name)
    else:
        raise KeyError(("Table name must be one of: {}".format(list(sorted(available_table_names)))))
