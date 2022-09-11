import os
import xml.etree.ElementTree as et
import shutil
import re
import pandas as pd
from . import global_var as gval

from loguru import logger
'''
使用Thwh版武器模板的wiki生成器
'''

WEAPON_PARAMS = [
    "武器编号",
    "弹头类型",
    "伤害类型",
    "致死/伤害",
    "绝对追伤",
    "衰减开始时间",
    "衰减结束时间",
    "是否消音",
    "自动化程度",
    "单次击发间隔",
    "视距",
    "移动速度修改量",
    "被发现率修改量",
    "抗致死性修改量",
    "弹匣容量",
    "单次上弹数",
    "散步范围",
    "初始精准度",
    "后坐力增长率",
    "后坐力回复率",
    "单次击发弹丸抛射量",
    "单次射击连续击发次数",
    "连续击发每两次击发间隔",
    "所属",
    "武器类型",
    "图片名称",
]


def check_keys(weapon_attrs: dict):
    keys = WEAPON_PARAMS[:]
    for k in weapon_attrs.keys():
        keys.remove(k)

    if len(keys) != 0:
        err = "These keys are not defined:\n"
        for k in keys:
            err += f"{' '*4}{k}\n"
        raise ValueError(err)
    else:
        logger.debug("All keys are defined")


def get_hasAttribute(spec: et.Element, attrname: str, default: str = ''):
    if attrname in spec.attrib.keys():
        return spec.attrib[attrname]
    else:
        return default


def parse_text(mod_text_path: str = ""):
    name2text = {}
    # 读取翻译
    if len(mod_text_path) != 0:
        tree = et.parse(mod_text_path)
        for elem in tree.iter(tag="text"):
            key = elem.attrib["key"]
            text = elem.attrib["text"]
            name2text[key] = text
        return name2text


def read_specification(weapon_attrs: dict, spec: et.Element):

    # 1
    weapon_attrs["单次击发间隔"] = get_hasAttribute(spec, 'retrigger_time', '-1')

    # 2
    weapon_class = get_hasAttribute(spec, 'class', '0')
    if weapon_class == '0':
        weapon_class = '全自动'
    elif weapon_class == '1':
        weapon_class = '手动'
    elif weapon_class == '2':
        weapon_class = '手动'
    elif weapon_class == '3':
        weapon_class = '不显示弹药'
    elif weapon_class == '4':
        weapon_class = '半自动'
    elif weapon_class == '5':
        weapon_class = '消耗物/部署物'
    else:
        weapon_class = 'N/A'
    weapon_attrs["自动化程度"] = weapon_class

    # 3
    weapon_attrs["初始精准度"] = get_hasAttribute(spec, 'accuracy_factor', 1)

    # 4
    weapon_attrs["单次击发弹丸抛射量"] = get_hasAttribute(spec, 'projectiles_per_shot',
                                                 1)

    # 5
    weapon_attrs["单次射击连续击发次数"] = get_hasAttribute(spec, 'burst_shots', 1)

    # 6
    weapon_attrs["连续击发每两次击发间隔"] = get_hasAttribute(
        spec, 'last_burst_retrigger_time')

    # 7
    weapon_attrs["后坐力增长率"] = get_hasAttribute(spec, 'sustained_fire_grow_step')

    # 8
    weapon_attrs["后坐力回复率"] = get_hasAttribute(spec,
                                              'sustained_fire_diminish_rate')

    # 9
    weapon_attrs["弹匣容量"] = spec.attrib['magazine_size']

    # 10
    # 如果reload_one_at_a_time为0或者它不存在都是一次性装满
    # 如果为1则要看动画才能知道，交给写wiki的人填
    value = get_hasAttribute(spec, 'reload_one_at_a_time', '0')
    weapon_attrs["单次上弹数"] = weapon_attrs["弹匣容量"] if value == '0' else 'Unknown'

    # 10
    weapon_attrs["视距"] = get_hasAttribute(spec, 'sight_range_modifier', 1)

    # 11
    weapon_attrs["散步范围"] = get_hasAttribute(spec, 'spread_range')

    # 12
    suppressed = get_hasAttribute(spec, 'suppressed', '0')
    weapon_attrs["是否消音"] = '是' if suppressed == '1' else '否'

    return spec.attrib['name']


def read_result(weapon_attrs: dict, result: et.Element):

    projectile_class = result.attrib['class']
    if projectile_class == 'hit':
        projectile_class = '动能'
        weapon_attrs["致死/伤害"] = get_hasAttribute(result, 'kill_probability')
    elif projectile_class == 'blast':
        projectile_class = '爆炸'
        weapon_attrs["致死/伤害"] = get_hasAttribute(result, 'damage')
    elif projectile_class == 'notify_script':
        projectile_class = '脚本'
    elif projectile_class == 'spawn':
        projectile_class = '子母弹'
    else:
        raise ValueError(
            f"projectile_class: {projectile_class} is not defined")

    weapon_attrs["弹头类型"] = projectile_class

    damage_cls = get_hasAttribute(result, 'character_state')
    if damage_cls == 'unwound':
        damage_cls = '治疗'
    elif damage_cls == '':
        damage_cls = 'death'
    weapon_attrs["伤害类型"] = damage_cls

    weapon_attrs["绝对追伤"] = get_hasAttribute(
        result, 'kill_probability_offset_on_successful_hit')

    weapon_attrs["衰减开始时间"] = get_hasAttribute(result, 'kill_decay_start_time')

    weapon_attrs["衰减结束时间"] = get_hasAttribute(result, 'kill_decay_end_time')


def read_projectile(weapon_attrs: dict, proj: et.Element):

    if proj != None:
        result = proj.find('result')
        if result != None:
            read_result(weapon_attrs, result)
        else:
            projectile_file = proj.attrib['file']
            projectile_path = mod_weapon_dir + '/' + projectile_file
            projectile_xml = et.parse(projectile_path)
            result = projectile_xml.find('result')
            if result != None:
                read_result(weapon_attrs, result)
            else:
                raise ValueError("Cant get projectile <result> tag")
    else:
        raise ValueError("Projectile is none")


def read_weapon(weapon: et.Element, out_folder: str):
    global weapon_attrs, name2text, all_weapon

    # 过滤key值
    key = weapon.attrib['key']
    if '_ai' in key or\
        'AI' in key:
        return

    # 读取specification中的数据
    specification = weapon.find('specification')
    name = read_specification(weapon_attrs, specification)
    try:
        text = name2text[name]
    except KeyError:
        text = name

    fname = key + '.txt'
    # name = text

    # 读取弹头中的数据
    projectile = weapon.find('projectile')
    read_projectile(weapon_attrs, projectile)

    # 读取Hud名字
    hud = weapon.find('hud_icon')
    weapon_attrs["图片名称"] = get_hasAttribute(hud, "filename")

    # 读取modifier
    modifier = weapon.findall('modifier')
    speed = 0
    detectability = 0
    hit_success_probability = 0

    for i in modifier:
        modifierClass = get_hasAttribute(i, 'class')
        if modifierClass == 'speed':
            speed = i.attrib['value']
        elif modifierClass == 'detectability':
            detectability = i.attrib['value']
        elif modifierClass == 'hit_success_probability':
            hit_success_probability = i.attrib['value']
        else:
            continue
    weapon_attrs["移动速度修改量"] = speed
    weapon_attrs["被发现率修改量"] = detectability
    weapon_attrs["抗致死性修改量"] = -float(hit_success_probability)

    # 默认的东西
    # 无

    check_keys(weapon_attrs)

    # 读取下一个的key
    next_element = weapon.find("next_in_chain")
    next_key = ""
    if next_element != None:
        next_key = get_hasAttribute(next_element, "key", "")

    output_file = out_folder + f'/{fname}'

    for k, v in weapon_attrs.items():
        if isinstance(v, str):
            try:
                weapon_attrs[k] = float(v)
            except:
                continue

    all_weapon[key] = {
        "weapon_attrs": weapon_attrs.copy(),
        "output_file": output_file,
        "next_key": next_key,
        "text": text,
        "name": name,
        "written": False,
    }


def parse_weapon_file(weapon_file: str, out_folder: str):
    weapon_path = mod_weapon_dir + '/' + weapon_file

    weapon_xml = et.parse(weapon_path)

    weapon = weapon_xml.getroot()

    if weapon.tag == "weapons":
        for w in weapon.findall("weapon"):
            read_weapon(w, out_folder)
    elif weapon.tag == "weapon":
        read_weapon(weapon, out_folder)


def parse_faction_weapon(faction_weapon_file: str,
                         output: str = 'output/faction',
                         in_rec=False):
    # 匹配阵营
    if faction_weapon_file.startswith('gk'):
        faction = 'G&K'
    elif faction_weapon_file.startswith('sf'):
        faction = 'SF'
    elif faction_weapon_file.startswith('kcco'):
        faction = 'KCCO'
    elif faction_weapon_file.startswith('paradeus'):
        faction = 'Paradeus'
    else:
        # faction = 'N/A'
        return

    logger.info(f"正在解析{faction}的武器文件{faction_weapon_file}")

    global weapon_attrs, all_weapon, REMOVE_OLD

    weapon_attrs["所属"] = faction

    faction_weapon_path = mod_weapon_dir + '/' + faction_weapon_file

    faction_weapon_xml = et.parse(faction_weapon_path)

    if faction == 'G&K':
        faction_folder = output + '/G&K武器'
        if REMOVE_OLD and os.path.exists(faction_folder):
            shutil.rmtree(faction_folder)
        # 读取gk_weapons.xml里的条目
        for node in faction_weapon_xml.iter(tag="weapon"):
            weapon_file = node.attrib["file"]
            # 匹配gk_weapons.xml里的嵌套武器文件
            xml_pattern = "gk_weapons_[3a-zA-Z_]+.xml"
            # gkw_编号_类型_弹头_名字
            # gkw_编号_类型_弹头_名字_MOD3
            # 为什么是_only呢？我不明白
            weap_pattern = "gkw_[0-9]+_((ar)|(smg)|(hg)|(rf)|(sg)|(mg))_[0-9a-zA-Z.-]+_[0-9a-zA-Z.]+(_[0-9a-zA-Z]+)?((_MOD3)|(_mod3))?(_skill)?(_only)?.weapon"
            # 前面两种_skill，以前的老命名文件了
            # 前面两种_皮肤编号_SKIN，以前的老命名文件了
            skin_pattern = "gkw_[0-9]+_((ar)|(smg)|(hg)|(rf)|(sg)|(mg))_[0-9a-zA-Z.-]+_[0-9a-zA-Z.]+(_[0-9a-zA-Z]+)?((_MOD3)|(_mod3))?_[0-9a-zA-Z]+_SKIN(_skill)?(_only)?.weapon"
            # 一些不同命名格式的文件
            diff_pattern = "((gkw_special_cyclops)|(target)|(gkw_medical_agl_hg)).weapon"
            # HVY武器
            hvy_pattern = "gkw_((hvy)|(228_smg_8x22_type100_banzai)|(hvypdw))[a-z0-9_]*.weapon"

            if re.match(xml_pattern, weapon_file) is not None:
                REMOVE_OLD = False
                parse_faction_weapon(weapon_file, output, True)
                REMOVE_OLD = True
            elif weapon_file.startswith("FF"):
                weapon_folder = faction_folder + f'/融合势力类'
                os.makedirs(weapon_folder, exist_ok=True)

                weapon_attrs["武器编号"] = ""
                weapon_attrs["武器类型"] = "FF"
                parse_weapon_file(weapon_file, weapon_folder)
            elif re.match(hvy_pattern, weapon_file) is not None:
                weapon_folder = faction_folder + f'/HVY'
                os.makedirs(weapon_folder, exist_ok=True)

                weapon_attrs["武器编号"] = ""
                weapon_attrs["武器类型"] = "HVY"
                parse_weapon_file(weapon_file, weapon_folder)
            elif re.match(diff_pattern, weapon_file) is not None:
                weapon_folder = faction_folder + f'/特殊'
                os.makedirs(weapon_folder, exist_ok=True)

                weapon_attrs["武器编号"] = ""
                weapon_attrs["武器类型"] = "特殊武器"
                parse_weapon_file(weapon_file, weapon_folder)
            elif re.match(skin_pattern, weapon_file) is not None:
                s = weapon_file.split('_')
                weapon_id = int(s[1])
                if weapon_id == 404:
                    # logger.info(f"跳过{weapon_file}的处理")
                    continue
                weapon_type = s[2].upper()
                weapon_folder = faction_folder + f'/{weapon_type}皮肤'
                os.makedirs(weapon_folder, exist_ok=True)

                weapon_attrs["武器编号"] = weapon_id
                weapon_attrs["武器类型"] = f'{weapon_type}皮肤'
                parse_weapon_file(weapon_file, weapon_folder)
            elif re.match(weap_pattern, weapon_file) is not None:
                s = weapon_file.split('_')
                weapon_id = int(s[1])
                if weapon_id == 404:
                    # logger.info(f"跳过{weapon_file}的处理")
                    continue
                weapon_type = s[2].upper()
                weapon_folder = faction_folder + f'/{weapon_type}'
                os.makedirs(weapon_folder, exist_ok=True)

                weapon_attrs["武器编号"] = weapon_id
                weapon_attrs["武器类型"] = weapon_type
                parse_weapon_file(weapon_file, weapon_folder)
            else:
                logger.info(f"跳过{weapon_file}的处理")
                continue
        if not in_rec:
            logger.info(f"{faction}一共处理了{len(all_weapon.keys())}把武器")
            faction_all_weapon[f"{faction}武器"] = all_weapon
    elif faction == 'SF':
        faction_folder = output + '/SF武器'
        if REMOVE_OLD and os.path.exists(faction_folder):
            shutil.rmtree(faction_folder)
        # 读取sf_weapons.xml里的条目
        for node in faction_weapon_xml.iter(tag="weapon"):
            weapon_file = node.attrib["file"]
            weapon_folder = faction_folder + f'/武器'
            os.makedirs(weapon_folder, exist_ok=True)

            weapon_attrs["武器编号"] = ""
            weapon_attrs["武器类型"] = "SF武器"
            parse_weapon_file(weapon_file, weapon_folder)
        if not in_rec:
            logger.info(f"{faction}一共处理了{len(all_weapon.keys())}把武器")
            faction_all_weapon[f"{faction}武器"] = all_weapon
    elif faction == 'KCCO':
        faction_folder = output + '/KCCO武器'
        if REMOVE_OLD and os.path.exists(faction_folder):
            shutil.rmtree(faction_folder)
        # 读取kcco_weapons.xml里的条目
        for node in faction_weapon_xml.iter(tag="weapon"):
            weapon_file = node.attrib["file"]
            # 不好处理
            unhandlable = ["othrusdog", "dactyl"]
            pass_this = False
            for u in unhandlable:
                if u in weapon_file:
                    pass_this = True
                    break
            if pass_this:
                continue
            weapon_folder = faction_folder + f'/武器'
            os.makedirs(weapon_folder, exist_ok=True)

            weapon_attrs["武器编号"] = ""
            weapon_attrs["武器类型"] = "KCCO武器"
            parse_weapon_file(weapon_file, weapon_folder)
        if not in_rec:
            logger.info(f"{faction}一共处理了{len(all_weapon.keys())}把武器")
            faction_all_weapon[f"{faction}武器"] = all_weapon
    elif faction == 'Paradeus':
        faction_folder = output + '/Paradeus武器'
        if REMOVE_OLD and os.path.exists(faction_folder):
            shutil.rmtree(faction_folder)
        # 读取paradeus_weapons.xml里的条目
        for node in faction_weapon_xml.iter(tag="weapon"):
            weapon_file = node.attrib["file"]
            if weapon_file.startswith("parw") or weapon_file.startswith(
                    "eild"):
                # 不好处理
                unhandlable = ["infected"]
                pass_this = False
                for u in unhandlable:
                    if u in weapon_file:
                        pass_this = True
                        break
                if pass_this:
                    continue
                weapon_folder = faction_folder + f'/武器'
                os.makedirs(weapon_folder, exist_ok=True)

                weapon_attrs["武器编号"] = ""
                weapon_attrs["武器类型"] = "Paradeus武器"
                parse_weapon_file(weapon_file, weapon_folder)
        if not in_rec:
            logger.info(f"{faction}一共处理了{len(all_weapon.keys())}把武器")
            faction_all_weapon[f"{faction}武器"] = all_weapon


def parse_all_weapon(mod_wp_dir: str,
                     all_weapon_path: str,
                     mod_text_path: str = ""):
    '''
    目前的唯一解析入口
    '''
    global name2text
    name2text = parse_text(mod_text_path)

    global mod_weapon_dir
    mod_weapon_dir = mod_wp_dir

    all_weapon_xml = et.parse(all_weapon_path)

    global weapon_attrs, all_weapon, faction_all_weapon, REMOVE_OLD, cnt
    REMOVE_OLD = gval._global_dict["REMOVE_OLD"]
    faction_all_weapon = {}
    for node in all_weapon_xml.iter(tag="weapon"):
        weapon_attrs = {}
        all_weapon = {}
        parse_faction_weapon(node.attrib["file"])
    cnt = 0
    for k, v in faction_all_weapon.items():
        write_weapon_txt(v)
    return faction_all_weapon, WEAPON_PARAMS


async def parse_merged_weapon(merged_weapon_path: str,
                              mod_text_path: str = ""):

    parse_text(mod_text_path)

    tree = et.parse(merged_weapon_path)

    # merged_weapon = merged_weapon_xml.findall

    global keys_name_text, existed
    existed = []
    keys_name_text = []
    for elem in tree.iter(tag="weapon"):
        key = elem.attrib['key']
        if 'ai' in key:
            continue
        if 'gk' not in key and 'ff' not in key:
            continue
        spec = elem.find('specification')

        name = spec.attrib['name']
        try:
            text = name2text[name]
        except KeyError:
            text = name
        if key in existed:
            continue
        keys_name_text.append((key, name, text))
        existed.append(key)
    print(f"一共搞了{len(keys_name_text)}把武器")
    return (("Key", "Name", "Text"), keys_name_text)


def write_weapon_txt(state_dict: dict):
    DO_WRITE_TXT = gval._global_dict["DO_WRITE_TXT"]
    if not DO_WRITE_TXT:
        return

    def write_one(weapon_attrs: dict = None,
                  output_file: str = None,
                  text: str = None,
                  name: str = None,
                  written=None,
                  next_key=None):
        '''
        传入的**dict里带有written, next_key，这里需要占位，否则报错
        '''
        global cnt

        logger.debug(f"正在写入{os.path.basename(output_file)}的文件")
        cnt += 1
        logger.info(f"第{cnt}个武器：写入{output_file}")

        f = open(output_file, 'w', encoding='utf-8')
        # 名字里不能带 # < > [ ] | { }，并且不要在标题处使用“特殊："
        paires = [
            ["-[", "("],
            [" [", "("],
            ["[", "("],
            ["]", ")"],
            ["_", " "]
        ]
        for p in paires:
            text = text.replace(p[0], p[1])
            name = name.replace(p[0], p[1])
        txt = f"中文名：{text}\n英文名：{name}\n"
        txt += "{{武器模板ForThwh\n"
        for k in WEAPON_PARAMS:
            txt += f"|{k}={weapon_attrs[k]}\n"
        txt += "}}\n"

        f.write(txt)
        f.close()

    def write_batch(batch: list):
        for b in batch:
            write_one(**b)

    def get_key_diff(key1: str, key2: str):
        # l = [key1, key2].sort(lambda x: len(x))
        l = sorted([key1, key2], key=lambda x: len(x))
        shorter, longer = l[0], l[1]
        shorter = shorter.replace(".weapon", "")
        longer = longer.replace(".weapon", "")
        al = []
        bl = []
        for i in range(min(len(shorter), len(longer))):
            a, b = shorter[i], longer[i]
            if a != b:
                al.append(a)
                bl.append(b)
        if len(key1) != len(key2):
            bl.extend(longer[i + 1:len(longer)])
        return "".join(al), "".join(bl)

    for k, v in state_dict.items():
        if not v["written"]:
            key = k
            batch = [v]
            state_dict[key]["written"] = True
            next_key = v["next_key"]

            while len(next_key) != 0:
                try:
                    if state_dict[next_key]["written"] == False:
                        pass
                    else:
                        break
                except KeyError as e:
                    logger.error(
                        f"{next_key} found in file but not in dictionary")
                    break

                next_v = state_dict[next_key].copy()
                if v["text"] == next_v["text"]:
                    diff1, diff2 = get_key_diff(key, next_key)
                    next_v["text"] += diff2
                batch.append(next_v.copy())
                state_dict[next_key]["written"] = True
                key = next_key
                v = state_dict[key]
                next_key = next_v["next_key"]

                # next_ptr = state_dict[ptr]["next_key"]
                # diff = "".join(list(set(ptr).difference(set(next_ptr))))
                # diff = "".join([i for i in next_ptr if i not in ptr])

            write_batch(batch)
