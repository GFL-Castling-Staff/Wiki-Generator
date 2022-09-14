from collections import defaultdict
import os
import shutil
import xml.etree.ElementTree as et

from loguru import logger
from .parse_weapon import get_hasAttribute, parse_text, read_projectile, read_specification
from . import global_var as gval

VEHICLE_PARAMS = [
    "生命值",
    "质量",
    "推动阈值",
    "重生时间",
    "爆炸伤害阈值",
    "爆炸伤害削减量",
    "炮塔描述",
    "最大前进时速",
    "加速度",
    "撞人所需时速",
    "最大倒车时速",
    "最大转弯角度",
    "能否水上行驶",
    "最大涉水深度",
    "瘫痪时生命值",
    "页面分类",
    "所属"
]


def check_keys(vehicle_attrs: dict):
    keys = VEHICLE_PARAMS[:]
    for k in vehicle_attrs.keys():
        keys.remove(k)

    if len(keys) != 0:
        err = "These keys are not defined:\n"
        for k in keys:
            err += f"{' '*4}{k}\n"
        raise ValueError(err)
    else:
        logger.debug("All keys are defined")


def query_merged_weapon(merged_weapon_path: str, keys:list):

    def get_descrip(weapon:et.Element):
        weapon_attrs = {}
        specification = weapon.find('specification')
        name = read_specification(weapon_attrs, specification)
        try:
            text = name2text[name]
        except KeyError:
            text = name

        ret = f"{text}: "
        ret += "装填时间{}s".format(weapon_attrs["单次击发间隔"])
        projectile = weapon.find('projectile')
        read_projectile(weapon_attrs, projectile)
        proj_cls = weapon_attrs["弹头类型"]
        if proj_cls == '动能':
            ret += ", {}致死".format(weapon_attrs["致死/伤害"])
            if weapon_attrs["绝对追伤"] != '':
                ret += "{}追伤".format(weapon_attrs["绝对追伤"])
            ret += "hit伤害"
        elif proj_cls == '爆炸':
            ret += ", {}blast伤害".format(weapon_attrs["致死/伤害"])
        else:
            ret += "无伤害信息"
        return ret.strip("\n")

    if "tree" not in globals().keys():
        global tree
        tree = et.parse(merged_weapon_path)

    ret = {}

    for elem in tree.iter(tag="weapon"):
        key = elem.attrib['key']
        if key in keys:
            ret[key] = get_descrip(elem)
            keys.remove(key)
            if len(keys) == 0:
                break
    return ret


def read_turret(turret_attrs: dict, turret: et.Element):
    merged_weapon_path = r"E:\SteamLibrary\steamapps\workshop\content\270150\2606099273\media\packages\GFL_Castling\weapons\merged_weapon.weapon"
    key = turret.attrib["weapon_key"]
    turret_attrs.update(query_merged_weapon(merged_weapon_path, [key]))


def read_physics(vehicle_attrs: dict, physics: et.Element):
    vehicle_attrs["质量"] = physics.attrib["mass"]
    vehicle_attrs["生命值"] = physics.attrib["max_health"]
    vehicle_attrs["推动阈值"] = get_hasAttribute(physics, "blast_push_threshold")
    vehicle_attrs["爆炸伤害阈值"] = get_hasAttribute(physics, "blast_damage_threshold")


def read_control(vehicle_attrs: dict, control: et.Element):
    vehicle_attrs["最大前进时速"] = control.attrib["max_speed"]
    vehicle_attrs["加速度"] = control.attrib["acceleration"]
    vehicle_attrs["最大倒车时速"] = control.attrib["max_reverse_speed"]
    vehicle_attrs["最大转弯角度"] = control.attrib["max_rotation"]
    vehicle_attrs["能否水上行驶"] = get_hasAttribute(control, "can_steer_in_water")
    vehicle_attrs["最大涉水深度"] = control.attrib["max_water_depth"]
    vehicle_attrs["瘫痪时生命值"] = get_hasAttribute(control, "min_health_to_steer")


def read_vehicle(vehicle: et.Element, out_folder: str):
    global vehicle_attrs

    vehicle_attrs["撞人所需时速"] = get_hasAttribute(
        vehicle, "max_character_collision_speed")
    vehicle_attrs["重生时间"] = get_hasAttribute(vehicle, "respawn_time")

    # 读取control
    read_control(vehicle_attrs, vehicle.find("control"))
    
    # 读取physics
    read_physics(vehicle_attrs, vehicle.find("physics"))
    
    # 读取turret
    turret_attrs = {}
    for turret in vehicle.findall("turret"):
        read_turret(turret_attrs, turret)
    vehicle_attrs["炮塔描述"] = '\n'.join(turret_attrs.values())
    
    # 读取modifier
    modifier = vehicle.findall('modifier')
    blast_damage = 0

    for i in modifier:
        modifierClass = get_hasAttribute(i, 'class')
        if modifierClass == 'blast_damage':
            blast_damage = i.attrib['value']
        else:
            continue
    vehicle_attrs["爆炸伤害削减量"] = -float(blast_damage)

    name = vehicle.attrib["name"]

    key = vehicle.attrib['key']
    output_file = out_folder + f"/{key}.txt"

    global name2text

    try:
        text = name2text[name]
    except KeyError:
        text = name

    check_keys(vehicle_attrs)

    for k, v in vehicle_attrs.items():
        if isinstance(v, str):
            try:
                vehicle_attrs[k] = float(v)
            except:
                continue

    global keys_vehicleinfos
    keys_vehicleinfos[key] = {
        "vehicle_attrs": vehicle_attrs.copy(),
        "output_file": output_file,
        "text": text,
        "name": name,
    }


def _parse_vehicle_file(vehicle_file: str, out_folder: str):
    vehicle_path = mod_vehicles_dir + f'/{vehicle_file}'
    vehicle_xml = et.parse(vehicle_path)

    vehicle = vehicle_xml.getroot()
    read_vehicle(vehicle, out_folder)


def parse_vehicle_file(vehicle_file: str, output: str = 'output/faction'):
    # 匹配阵营
    if vehicle_file.startswith('gk') and not vehicle_file.endswith('store.vehicle'):
        faction = 'G&K'
    elif vehicle_file.startswith(('sf')):
        faction = 'SF'
    elif vehicle_file.startswith('kcco'):
        faction = 'KCCO'
    elif vehicle_file.startswith('par'):
        faction = 'Paradeus'
    else:
        logger.warning(f"未知阵营文件{vehicle_file}将跳过")
        return

    logger.info(f"正在解析{faction}的载具文件{vehicle_file}")
    global keys_vehicleinfos, vehicle_attrs, factions_vehicles, REMOVE_OLD, removed
    vehicle_attrs["所属"] = faction
    vehicle_attrs["页面分类"] = f'{faction}载具'

    # 以防以后各个阵营的护甲有不同之处，每个阵营用一个if语句来分离
    if faction == 'G&K':
        faction_folder = output + f'/{faction}载具'
        if not removed[f'/{faction}载具'] and REMOVE_OLD and os.path.exists(
                faction_folder):
            shutil.rmtree(faction_folder)
            removed[f'/{faction}载具'] = True

        vehicle_folder = faction_folder + '/载具'
        os.makedirs(vehicle_folder, exist_ok=True)
        _parse_vehicle_file(vehicle_file, vehicle_folder)

        factions_vehicles[f"{faction}载具"].update(keys_vehicleinfos)
    elif faction == 'SF':
        faction_folder = output + f'/{faction}载具'
        if not removed[f'/{faction}载具'] and REMOVE_OLD and os.path.exists(
                faction_folder):
            shutil.rmtree(faction_folder)
            removed[f'/{faction}载具'] = True

        vehicle_folder = faction_folder + '/载具'
        os.makedirs(vehicle_folder, exist_ok=True)
        _parse_vehicle_file(vehicle_file, vehicle_folder)

        factions_vehicles[f"{faction}载具"].update(keys_vehicleinfos)
    elif faction == 'KCCO':
        faction_folder = output + f'/{faction}载具'
        if not removed[f'/{faction}载具'] and REMOVE_OLD and os.path.exists(
                faction_folder):
            shutil.rmtree(faction_folder)
            removed[f'/{faction}载具'] = True

        vehicle_folder = faction_folder + '/载具'
        os.makedirs(vehicle_folder, exist_ok=True)
        _parse_vehicle_file(vehicle_file, vehicle_folder)

        factions_vehicles[f"{faction}载具"].update(keys_vehicleinfos)
    elif faction == 'Paradeus':
        faction_folder = output + f'/{faction}载具'
        if not removed[f'/{faction}载具'] and REMOVE_OLD and os.path.exists(
                faction_folder):
            shutil.rmtree(faction_folder)
            removed[f'/{faction}载具'] = True

        vehicle_folder = faction_folder + '/载具'
        os.makedirs(vehicle_folder, exist_ok=True)
        _parse_vehicle_file(vehicle_file, vehicle_folder)

        factions_vehicles[f"{faction}载具"].update(keys_vehicleinfos)


def parse_Castling_vehicles(mod_v_dir: str, Castling_vehicles_path: str,
                            mod_text_path: str):

    global name2text
    name2text = parse_text(mod_text_path)

    global mod_vehicles_dir
    mod_vehicles_dir = mod_v_dir

    global vehicle_attrs, cnt, keys_vehicleinfos, factions_vehicles, REMOVE_OLD, removed
    removed = defaultdict(lambda: False)
    REMOVE_OLD = gval._global_dict["REMOVE_OLD"]

    factions_vehicles = defaultdict(dict)
    keys_vehicleinfos = {}
    vehicle_attrs = {}

    xml = et.parse(Castling_vehicles_path)
    for item in xml.iter("vehicle"):
        parse_vehicle_file(item.attrib["file"])

    cnt = 0
    for k, v in factions_vehicles.items():
        write_vehicle_txt(v)

    return factions_vehicles, VEHICLE_PARAMS


def write_vehicle_txt(state_dict: dict):
    DO_WRITE_TXT = gval._global_dict["DO_WRITE_TXT"]
    if not DO_WRITE_TXT:
        return

    def write_one(
        vehicle_attrs: dict = None,
        output_file: str = None,
        text: str = None,
        name: str = None,
    ):
        global cnt

        logger.debug(f"正在写入{os.path.basename(output_file)}的文件")
        cnt += 1
        logger.info(f"第{cnt}个载具：写入{output_file}")

        f = open(output_file, 'w', encoding='utf-8')
        # 名字里不能带 # < > [ ] | { }，并且不要在标题处使用“特殊："
        paires = [["-[", "("], [" [", "("], ["[", "("], ["]", ")"], ["_", " "]]
        for p in paires:
            text = text.replace(p[0], p[1])
            name = name.replace(p[0], p[1])
        txt = f"中文名：{text}\n英文名：{name}\n"
        txt += "{{载具模板ForThwh\n"
        for k in VEHICLE_PARAMS:
            txt += f"|{k}={vehicle_attrs[k]}\n"
        txt += "}}\n"

        f.write(txt)
        f.close()

    for k in state_dict.keys():
        write_one(**state_dict[k])
