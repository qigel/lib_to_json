from liberty.parser import parse_liberty
from liberty.types import EscapedString
import json


def encode_escaped_string(s):
    if isinstance(s, EscapedString):
        return s.value
    else:
        type_name = s.__class__.__name__
        raise TypeError(f"Object of type '{type_name}' is not JSON serializable")


def lib_to_json(liberty_file, json_file):
    library = parse_liberty(open(liberty_file).read())
    JSON_dict = dict()
    attr_cnt = dict()
    for attr in library.attributes:
        if attr_cnt.get(attr.name) is None:
            attr_cnt[attr.name] = 1
        else:
            attr_cnt[attr.name] += 1
    for attr in library.attributes:
        if attr_cnt[attr.name] == 1:
            JSON_dict[attr.name] = attr.value
        else:
            if JSON_dict.get('comp_attribute,' + attr.name) is None:
                JSON_dict['comp_attribute,' + attr.name] = list()
            JSON_dict['comp_attribute,' + attr.name].append(attr.value)
    JSON_dict['define'] = list()
    for define in library.defines:
        JSON_dict['define'].append(
            dict(attribute_name=define.attribute_name, attribute_type=define.attribute_type,
                 group_name=define.group_name))
    for group in library.groups:
        if group.group_name != 'cell':
            JSON_dict[group.group_name + ',' + group.args[0].value] = dict()
            attr_cnt = dict()
            for attr in group.attributes:
                if attr_cnt.get(attr.name) is None:
                    attr_cnt[attr.name] = 1
                else:
                    attr_cnt[attr.name] += 1
            for attr in group.attributes:
                if attr_cnt[attr.name] == 1:
                    JSON_dict[group.group_name + ',' + group.args[0].value][attr.name] = attr.value
                else:
                    if JSON_dict[group.group_name + ',' + group.args[0].value].get(
                            'comp_attribute,' + attr.name) is None:
                        JSON_dict[group.group_name + ',' + group.args[0].value]['comp_attribute,' + attr.name] = list()
                    JSON_dict[group.group_name + ',' + group.args[0].value]['comp_attribute,' + attr.name].append(
                        attr.value)
    JSON_dict['cells'] = dict()
    for cell in library.groups:
        if cell.group_name == 'cell':
            JSON_dict['cells'][cell.args[0].value] = dict()
            attr_cnt = dict()
            for attr in cell.attributes:
                if attr_cnt.get(attr.name) is None:
                    attr_cnt[attr.name] = 1
                else:
                    attr_cnt[attr.name] += 1
            for attr in cell.attributes:
                if attr_cnt[attr.name] == 1:
                    JSON_dict['cells'][cell.args[0].value][attr.name] = attr.value
                else:
                    if JSON_dict['cells'][cell.args[0].value].get('comp_attribute,' + attr.name) is None:
                        JSON_dict['cells'][cell.args[0].value]['comp_attribute,' + attr.name] = list()
                    JSON_dict['cells'][cell.args[0].value]['comp_attribute,' + attr.name].append(attr.value)
            for group in cell.groups:
                if group.args[0] is None:
                    if JSON_dict['cells'][cell.args[0].value].get(group.group_name) is None:
                        JSON_dict['cells'][cell.args[0].value][group.group_name] = list()
                    JSON_dict['cells'][cell.args[0].value][group.group_name].append(dict())
                    attr_cnt = dict()
                    for attr in group.attributes:
                        if attr_cnt.get(attr.name) is None:
                            attr_cnt[attr.name] = 1
                        else:
                            attr_cnt[attr.name] += 1
                    for attr in group.attributes:
                        if attr_cnt[attr.name] == 1:
                            JSON_dict['cells'][cell.args[0].value][group.group_name][-1][attr.name] = attr.value
                        else:
                            if JSON_dict['cells'][cell.args[0].value][group.group_name][-1].get(
                                    'comp_attribute,' + attr.name) is None:
                                JSON_dict['cells'][cell.args[0].value][group.group_name][-1][
                                    'comp_attribute,' + attr.name] = list()
                            JSON_dict['cells'][cell.args[0].value][group.group_name][-1][
                                'comp_attribute,' + attr.name].append(attr.value)
                else:
                    JSON_dict['cells'][cell.args[0].value][group.group_name + ',' + group.args[0].value] = dict()
                    attr_cnt = dict()
                    for attr in group.attributes:
                        if attr_cnt.get(attr.name) is None:
                            attr_cnt[attr.name] = 1
                        else:
                            attr_cnt[attr.name] += 1
                    for attr in group.attributes:
                        if attr_cnt[attr.name] == 1:
                            JSON_dict['cells'][cell.args[0].value][group.group_name + ',' + group.args[0].value][
                                attr.name] = attr.value
                        else:
                            if JSON_dict['cells'][cell.args[0].value][group.group_name + ',' + group.args[0].value].get(
                                    'comp_attribute,' + attr.name) is None:
                                JSON_dict['cells'][cell.args[0].value][group.group_name + ',' + group.args[0].value][
                                    'comp_attribute,' + attr.name] = list()
                            JSON_dict['cells'][cell.args[0].value][group.group_name + ',' + group.args[0].value][
                                'comp_attribute,' + attr.name].append(attr.value)
                    for gr1 in group.groups:
                        JSON_dict['cells'][cell.args[0].value][group.group_name + ',' + group.args[0].value][
                            gr1.group_name] = dict()
                        for gr2 in gr1.groups:
                            JSON_dict['cells'][cell.args[0].value][group.group_name + ',' + group.args[0].value][
                                gr1.group_name][gr2.group_name + ',' + gr2.args[0].value] = dict()
                            attr_cnt = dict()
                            for attr in gr2.attributes:
                                if attr_cnt.get(attr.name) is None:
                                    attr_cnt[attr.name] = 1
                                else:
                                    attr_cnt[attr.name] += 1
                            for attr in gr2.attributes:
                                if attr_cnt[attr.name] == 1:
                                    JSON_dict['cells'][cell.args[0].value][
                                        group.group_name + ',' + group.args[0].value][
                                        gr1.group_name][gr2.group_name + ',' + gr2.args[0].value][
                                        attr.name] = attr.value
                                else:
                                    if JSON_dict['cells'][cell.args[0].value][
                                        group.group_name + ',' + group.args[0].value][
                                        gr1.group_name][gr2.group_name + ',' + gr2.args[0].value].get(
                                        'comp_attribute,' + attr.name) is None:
                                        JSON_dict['cells'][cell.args[0].value][
                                            group.group_name + ',' + group.args[0].value][
                                            gr1.group_name][gr2.group_name + ',' + gr2.args[0].value][
                                            'comp_attribute,' + attr.name] = list()
                                    JSON_dict['cells'][cell.args[0].value][
                                        group.group_name + ',' + group.args[0].value][
                                        gr1.group_name][gr2.group_name + ',' + gr2.args[0].value][
                                        'comp_attribute,' + attr.name].append(attr.value)
    json.dump(JSON_dict, open(json_file, 'w'), default=encode_escaped_string)
