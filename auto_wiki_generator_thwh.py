import os
import traceback
from scripts import parse_all_weapon, parse_all_carryitem, parse_Castling_vehicles
from scripts import global_var as gval

from loguru import logger
from time import perf_counter, sleep

import pandas as pd


def make_dpsexcel(output: str = 'output/faction'):
    def enum_keys(type_folder):
        keys = []
        for file in os.scandir(type_folder):
            if file.is_file():
                keys.append(file.name.replace('.txt', ''))
        return keys

    def enum_type(faction_folder):
        keys = []
        for wtype in os.scandir(faction_folder):
            if wtype.is_dir():
                keys.extend(enum_keys(wtype.path))
        return keys

    xlsx_path = output + '/G&K武器DPS参考.xlsx'
    opened = False
    while not opened:
        try:
            writer = pd.ExcelWriter(xlsx_path)
            opened = True
        except Exception as e:
            logger.error(traceback.format_exc())
            sleep(2)
    workbook = writer.book

    workbook_dict = {}
    enemydata = (('普通', '0.6'), ('较肉', '0.8'), ('盾兵', '1'), ('机械', '1.4'),
                 ('意外', '1.6'))
    for item in os.scandir(output):
        if item.is_dir() and item.name.startswith(
                "G&K") and item.name.endswith("武器"):
            sheet_name = item.name
            workbook_dict[sheet_name] = {"list": []}
            name_max_len = 0

            column = WEAPON_PARAMS.copy()
            column.insert(1, "武器名称")
            column.remove('所属')
            column.remove('图片名称')
            for k in enum_type(item.path):
                w_attrs = factions_weapons[sheet_name][k]
                w_attr = w_attrs['weapon_attrs']
                w_attr.pop('所属')
                w_attr.pop('图片名称')
                w_attr["武器名称"] = w_attrs["text"]
                if w_attr['弹头类型'] == '动能':
                    for e in enemydata:
                        kill_prob = float(w_attr['致死/伤害'])
                        anti_kill = float(e[1])
                        dph = (kill_prob - 1) // anti_kill
                        dph_prob = max(0,
                                       kill_prob - anti_kill * dph - anti_kill)
                        dph_expe = (1 - dph_prob) * dph + dph_prob * (dph + 1)
                        kill_offs = w_attr['绝对追伤']
                        kill_offs = float(kill_offs) if kill_offs != '' else 0
                        sumdph_expe = (1 - dph_prob) * (
                            dph + kill_offs) + dph_prob * (
                                dph + 1 + kill_offs
                            ) if dph > 0 else dph_prob * (1 + kill_offs)
                        interval = float(w_attr['单次击发间隔'])
                        dps = sumdph_expe * (1 / interval)
                        col_sum = f"对{e[0]}DPH总伤期望"
                        col_dps = f"对{e[0]}DPS"
                        w_attr[col_sum] = f"{sumdph_expe:g}"
                        w_attr[col_dps] = f"{dps:g}"
                        if col_sum not in column:
                            column.append(col_sum)
                            column.append(col_dps)
                elif w_attr['弹头类型'] == '爆炸':
                    for e in enemydata:
                        damage = float(w_attr['致死/伤害'])
                        warhead = float(w_attr['单次击发弹丸抛射量'])
                        sumdph_expe = damage * warhead
                        col_sum = f"对{e[0]}DPH总伤期望"
                        col_dps = f"对{e[0]}DPS"
                        w_attr[col_sum] = f"{sumdph_expe:g}"
                        w_attr[col_dps] = ''
                        if col_sum not in column:
                            column.append(col_sum)
                            column.append(col_dps)
                name_max_len = len(w_attrs["text"]) if len(
                    w_attrs["text"]) > name_max_len else name_max_len
                workbook_dict[sheet_name]["list"].append(w_attr)

            workbook_dict[sheet_name]["columns"] = column
            workbook_dict[sheet_name]["max_len"] = name_max_len

    for f, d in workbook_dict.items():
        df = pd.DataFrame(d["list"], columns=d["columns"])
        df.index = df.index + 1
        df.to_excel(writer, f, index=False)

        worksheet = writer.sheets[f]
        cell_format = workbook.add_format({
            "align": "left",
            "valign": "vcenter",
        })
        cell_format.set_text_wrap()
        for i, c in enumerate(d["columns"]):
            if c.endswith('名称'):
                width = d["max_len"] + 2
            elif c == "炮塔描述":
                width = len(c) * 16
            else:
                width = len(c) * 2
            worksheet.set_column(i, i, width, cell_format=cell_format)
        worksheet.freeze_panes(1, 0)
        worksheet.autofilter(0, 0, df.shape[0], df.shape[1] - 1)

    writer.save()
    logger.info(f"{xlsx_path}表格生成完毕")


def make_excel(output: str = 'output/faction'):
    def enum_keys(type_folder):
        keys = []
        for file in os.scandir(type_folder):
            if file.is_file():
                keys.append(file.name.replace('.txt', ''))
        return keys

    def enum_type(faction_folder):
        keys = []
        for wtype in os.scandir(faction_folder):
            if wtype.is_dir():
                keys.extend(enum_keys(wtype.path))
        return keys

    xlsx_path = output + '/武器护甲载具数据汇总.xlsx'
    opened = False
    while not opened:
        try:
            writer = pd.ExcelWriter(xlsx_path)
            opened = True
        except Exception as e:
            logger.error(traceback.format_exc())
            sleep(2)
    workbook = writer.book

    workbook_dict = {}
    for item in os.scandir(output):
        if item.is_dir():
            sheet_name = item.name
            workbook_dict[sheet_name] = {"list": []}
            name_max_len = 0

            if item.name.endswith("武器"):
                for k in enum_type(item.path):
                    w_attrs = factions_weapons[sheet_name][k]
                    w_attr = w_attrs['weapon_attrs']
                    w_attr.pop('所属')
                    w_attr.pop('图片名称')
                    w_attr["武器名称"] = w_attrs["text"]
                    name_max_len = len(w_attrs["text"]) if len(
                        w_attrs["text"]) > name_max_len else name_max_len
                    workbook_dict[sheet_name]["list"].append(w_attr)
                column = WEAPON_PARAMS.copy()
                column.insert(1, "武器名称")
                column.remove('所属')
                column.remove('图片名称')

            elif item.name.endswith("护甲"):
                for k in enum_type(item.path):
                    ci_attrs = faction_cis[sheet_name][k]
                    ci_attr = ci_attrs['ci_attrs']
                    ci_attr.pop('所属')
                    ci_attr.pop('图片名称')
                    ci_attr["护甲名称"] = ci_attrs["text"]
                    name_max_len = len(ci_attrs["text"]) if len(
                        ci_attrs["text"]) > name_max_len else name_max_len
                    workbook_dict[sheet_name]["list"].append(ci_attr)
                column = CARRY_PARAMS.copy()
                column.insert(0, "护甲名称")
                column.remove('所属')
                column.remove('图片名称')

            elif item.name.endswith("载具"):
                for k in enum_type(item.path):
                    vehicle_attrs = factions_vehicles[sheet_name][k]
                    vehicle_attr = vehicle_attrs['vehicle_attrs']
                    vehicle_attr.pop('所属')
                    vehicle_attr["载具名称"] = vehicle_attrs["text"]
                    vehicle_attr["炮塔描述"] = vehicle_attr["炮塔描述"].replace(
                        "<br>", "\n")
                    name_max_len = len(vehicle_attrs["text"]) if len(
                        vehicle_attrs["text"]) > name_max_len else name_max_len
                    workbook_dict[sheet_name]["list"].append(vehicle_attr)
                column = VEHICLE_PARAMS.copy()
                column.insert(0, "载具名称")
                column.remove('所属')

            workbook_dict[sheet_name]["columns"] = column
            workbook_dict[sheet_name]["max_len"] = name_max_len

    for f, d in workbook_dict.items():
        df = pd.DataFrame(d["list"], columns=d["columns"])
        df.index = df.index + 1
        df.to_excel(writer, f, index=False)

        worksheet = writer.sheets[f]
        cell_format = workbook.add_format({
            "align": "left",
            "valign": "vcenter",
        })
        cell_format.set_text_wrap()
        for i, c in enumerate(d["columns"]):
            if c.endswith('名称'):
                width = d["max_len"] + 2
            elif c == "炮塔描述":
                width = len(c) * 16
            else:
                width = len(c) * 2
            worksheet.set_column(i, i, width, cell_format=cell_format)
        worksheet.freeze_panes(1, 0)
        worksheet.autofilter(0, 0, df.shape[0], df.shape[1] - 1)

    writer.save()
    logger.info(f"{xlsx_path}表格生成完毕")


def generate_weapon(REMOVE_OLD, DO_WRITE_TXT=True):
    gval._init()
    gval.set_value("REMOVE_OLD", REMOVE_OLD)
    gval.set_value("DO_WRITE_TXT", DO_WRITE_TXT)

    st = perf_counter()
    global factions_weapons, WEAPON_PARAMS
    factions_weapons, WEAPON_PARAMS = parse_all_weapon(mod_weapon_dir,
                                                       all_weapon_path,
                                                       mod_text_path)


def generate_carryitem(REMOVE_OLD, DO_WRITE_TXT=True):
    gval._init()
    gval.set_value("REMOVE_OLD", REMOVE_OLD)
    gval.set_value("DO_WRITE_TXT", DO_WRITE_TXT)
    global faction_cis, CARRY_PARAMS
    faction_cis, CARRY_PARAMS = parse_all_carryitem(mod_items_dir,
                                                    all_carryitem_path,
                                                    mod_text_path)


def generate_vehicle(REMOVE_OLD, DO_WRITE_TXT=True):
    gval._init()
    gval.set_value("REMOVE_OLD", REMOVE_OLD)
    gval.set_value("DO_WRITE_TXT", DO_WRITE_TXT)
    global factions_vehicles, VEHICLE_PARAMS
    factions_vehicles, VEHICLE_PARAMS = parse_Castling_vehicles(
        mod_vehicles_dir, Castling_vehicles_path, mod_text_path)


def gen_template():
    from scripts import gen_part_template, VEHICLE_PARAMS, VEHICLE_CAN_EMPTY
    with open("output/gen_template.txt", "w") as f:
        f.write(gen_part_template(VEHICLE_PARAMS, VEHICLE_CAN_EMPTY))


if __name__ == "__main__":
    logger.add("output/wiki_generator_log.txt",
               encoding="utf-8",
               level="INFO",
               retention="10 seconds")

    mod_text_path = r"E:\SteamLibrary\steamapps\workshop\content\270150\2606099273\media\packages\GFL_Castling\languages\cn\misc_text.xml"

    mod_weapon_dir = r"E:\SteamLibrary\steamapps\workshop\content\270150\2606099273\media\packages\GFL_Castling\weapons"
    all_weapon_path = mod_weapon_dir + r"\all_weapons.xml"

    mod_items_dir = r"E:\SteamLibrary\steamapps\workshop\content\270150\2606099273\media\packages\GFL_Castling\items"
    all_carryitem_path = mod_items_dir + '/all_carry_items.xml'

    mod_vehicles_dir = r"E:\SteamLibrary\steamapps\workshop\content\270150\2606099273\media\packages\GFL_Castling\vehicles"
    Castling_vehicles_path = mod_vehicles_dir + '/GFL_Castling_vehicles.xml'

    # gen_template()
    # exit(0)

    a1 = True
    a2 = True
    a3 = True
    # a1 = False
    # a2 = False
    # a3 = False
    generate_weapon(a1, a1)
    generate_carryitem(a2, a2)
    generate_vehicle(a3, a3)

    # 以下两个函数无法同时运行
    make_excel()
    # make_dpsexcel()
    