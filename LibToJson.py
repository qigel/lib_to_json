from liberty.parser import parse_liberty
from liberty.types import *
import json
import ast


def encode_escaped_string(s):
    if isinstance(s, EscapedString):
        return str(s)
    elif isinstance(s, WithUnit):
        return str(s)
    elif isinstance(s, ArithExpression):
        return str(s)
    elif isinstance(s, NameBitSelection):
        return str(s)
    else:
        type_name = s.__class__.__name__
        raise TypeError(f"Object of type '{type_name}' is not JSON serializable")


def escaped_string_convert(obj):
    if isinstance(obj, Group):
        new_obj = Group(escaped_string_convert(obj.group_name))
        for group in obj.groups:
            group = escaped_string_convert(group)
            new_obj.groups.append(group)
        for attr in obj.attributes:
            attr = escaped_string_convert(attr)
            new_obj.attributes.append(attr)
        for arg in obj.args:
            arg = escaped_string_convert(arg)
            new_obj.args.append(arg)
        for define in obj.defines:
            define = escaped_string_convert(define)
            new_obj.defines.append(define)
        obj = new_obj
    elif isinstance(obj, Attribute):
        obj.value = escaped_string_convert(obj.value)
        obj.name = escaped_string_convert(obj.name)
    elif isinstance(obj, Define):
        obj.attribute_name = escaped_string_convert(obj.attribute_name)
        obj.attribute_type = escaped_string_convert(obj.attribute_type)
        obj.group_name = escaped_string_convert(obj.group_name)
    elif isinstance(obj, EscapedString):
        obj = str(obj)
    elif isinstance(obj, list):
        if isinstance(obj[0], EscapedString):
            try:
                obj = ast.literal_eval(str(obj))
            except:
                new_obj = list()
                for el in obj:
                    new_obj.append(escaped_string_convert(el))
                obj = new_obj
    return obj


def group_to_dict(group):
    out_dict = dict()
    attr_cnt = dict()
    for attr in group.attributes:
        if attr_cnt.get(attr.name) is None:
            attr_cnt[attr.name] = 1
        else:
            attr_cnt[attr.name] += 1
    for attr in group.attributes:
        if attr_cnt[attr.name] == 1:
            out_dict[attr.name] = attr.value
        else:
            if out_dict.get('comp_attribute,' + str(attr.name)) is None:
                out_dict['comp_attribute,' + str(attr.name)] = list()
            out_dict['comp_attribute,' + str(attr.name)].append(attr.value)
    if len(group.defines) != 0:
        out_dict['define'] = list()
        for define in group.defines:
            out_dict['define'].append(
                dict(attribute_name=define.attribute_name, attribute_type=define.attribute_type,
                     group_name=define.group_name))
    contains_cells = False
    for cgroup in group.groups:
        if cgroup.group_name == 'cell':
            contains_cells = True
        else:
            out_dict[str(cgroup.group_name) + ',' + str(cgroup.args[0])] = group_to_dict(cgroup)
    if contains_cells:
        out_dict['cells'] = dict()
        for cell in group.groups:
            if cell.group_name == 'cell':
                out_dict['cells'][cell.args[0]] = group_to_dict(cell)
    return out_dict


def lib_to_json(liberty_file, json_file):
    library = parse_liberty(open(liberty_file).read())
    library = escaped_string_convert(library)
    #JSON_dict = dict()
    JSON_dict = group_to_dict(library)
    json.dump(JSON_dict, open(json_file, 'w'), default=encode_escaped_string)
