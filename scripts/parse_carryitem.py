import os
import shutil
import xml.etree.ElementTree as et
import pandas as pd

from loguru import logger
from .parse_weapon import parse_text
from . import global_var as gval

CARRY_PARAMS = [
    "层数",
    "移动速度修改量",
    "被发现率修改量",
    "抗致死性修改量",
    "图片名称",
    "页面分类",
    "所属"
]

def check_keys(ci_attrs: dict):
    keys = CARRY_PARAMS[:]
    for k in ci_attrs.keys():
        keys.remove(k)

    if len(keys) != 0:
        err = "These keys are not defined:\n"
        for k in keys:
            err += f"{' '*4}{k}\n"
        raise ValueError(err)
    else:
        logger.debug("All keys are defined")

def read_ci(ci:et.Element, out_folder:str):
    speed = 0
    detectability = 0
    hit_success_probability = 0
    
    global ci_attrs
    for mod in ci.iter(tag="modifier"):
        cls = mod.attrib["class"]
        if cls == "speed":
            speed = mod.attrib["value"]
        elif cls == "detectability":
            detectability = mod.attrib["value"]
        elif cls == "hit_success_probability":
            hit_success_probability = mod.attrib["value"]

    name = ci.attrib["name"]
    hud_name = ci.find("hud_icon").attrib["filename"]
    ci_attrs["移动速度修改量"] = speed
    ci_attrs["被发现率修改量"] = detectability
    ci_attrs["抗致死性修改量"] = -float(hit_success_probability)
    ci_attrs["图片名称"] = hud_name
    
    key = ci.attrib['key']
    output_file = out_folder + f"/{key}.txt"
    global name2text

    try:
        text = name2text[name]
    except KeyError:
        text = name

    check_keys(ci_attrs)
    
    for k, v in ci_attrs.items():
        if isinstance(v, str):
            try:
                ci_attrs[k] = float(v)
            except:
                continue

    global all_ci
    all_ci[key] = {
        "ci_attrs": ci_attrs.copy(),
        "output_file": output_file,
        "text": text,
        "name": name,
    }


def parse_ci_file(ci_file:str, out_folder: str):
    ci_path = mod_items_dir + f'/{ci_file}'
    ci_xml = et.parse(ci_path)
    nodenum = 0
    key2node = {}
    headkey = ""
    for item in ci_xml.iter("carry_item"):
        key = item.attrib["key"]
        key2node[key] = item
        nodenum += 1
    failed = 0
    for k, v in key2node.items():
        try:
            nxt = v.attrib["transform_on_consume"]
        except:
            nxt = f"{k} didn't has nxt"
            failed += 1
            continue
        sortkey = [k]
        while nxt in key2node.keys():
            sortkey.append(key2node[nxt].attrib["key"])
            try:
                nxt = key2node[nxt].attrib["transform_on_consume"]
            except:
                nxt = f"{nxt} didn't has nxt"
        if len(sortkey) == nodenum:
            if headkey == "":
                headkey = k
                ci_attrs["层数"] = nodenum-1
                read_ci(v, out_folder)
            else:
                raise ValueError("Found two fullkey")
        else:
            failed += 1
    if failed == nodenum:
        for k, v in key2node.items():
            ci_attrs["层数"] = 1
            read_ci(v, out_folder)


def parse_faction_ci(faction_ci_file:str,
                         output: str = 'output/faction'):
    # 匹配阵营
    if faction_ci_file.startswith('gk'):
        faction = 'G&K'
    elif faction_ci_file.startswith('sf'):
        faction = 'SF'
    elif faction_ci_file.startswith('kcco'):
        faction = 'KCCO'
    elif faction_ci_file.startswith('pard'):
        faction = 'Paradeus'
    else:
        # faction = 'N/A'
        return

    logger.info(f"正在解析{faction}的护甲文件{faction_ci_file}")
    global all_ci, ci_attrs, faction_all_ci, REMOVE_OLD
    ci_attrs["所属"] = faction
    ci_attrs["页面分类"] = f'{faction}护甲'

    fac_ci_path = mod_items_dir + f'/{faction_ci_file}'
    fac_ci_xml = et.parse(fac_ci_path)
    # 以防以后各个阵营的护甲有不同之处，每个阵营用一个if语句来分离
    if faction == 'G&K':
        faction_folder = output + '/G&K护甲'

        for item in fac_ci_xml.iter(tag="carry_item"):
            ci_file = item.attrib["file"]
            # if "immunity" in ci_file:
            #     continue
            ci_folder = faction_folder + '/护甲'
            if REMOVE_OLD and os.path.exists(ci_folder):
                shutil.rmtree(ci_folder)
                REMOVE_OLD = False
            os.makedirs(ci_folder, exist_ok=True)
            parse_ci_file(ci_file, ci_folder)
        logger.info(f"{faction}一共处理了{len(all_ci.keys())}个护甲")
        faction_all_ci[f"{faction}护甲"] = all_ci
        # 要重新生成下一个阵营的文件夹
        REMOVE_OLD = True
    elif faction == 'SF':
        faction_folder = output + '/SF护甲'
        for item in fac_ci_xml.iter(tag="carry_item"):
            ci_file = item.attrib["file"]
            ci_folder = faction_folder + '/护甲'
            if REMOVE_OLD and os.path.exists(ci_folder):
                shutil.rmtree(ci_folder)
                REMOVE_OLD = False
            os.makedirs(ci_folder, exist_ok=True)
            parse_ci_file(ci_file, ci_folder)
        logger.info(f"{faction}一共处理了{len(all_ci.keys())}个护甲")
        faction_all_ci[f"{faction}护甲"] = all_ci
        # 要重新生成下一个阵营的文件夹
        REMOVE_OLD = True
    elif faction == 'KCCO':
        faction_folder = output + '/KCCO护甲'
        for item in fac_ci_xml.iter(tag="carry_item"):
            ci_file = item.attrib["file"]
            ci_folder = faction_folder + '/护甲'
            if REMOVE_OLD and os.path.exists(ci_folder):
                shutil.rmtree(ci_folder)
                REMOVE_OLD = False
            os.makedirs(ci_folder, exist_ok=True)
            parse_ci_file(ci_file, ci_folder)
        logger.info(f"{faction}一共处理了{len(all_ci.keys())}个护甲")
        faction_all_ci[f"{faction}护甲"] = all_ci
        # 要重新生成下一个阵营的文件夹
        REMOVE_OLD = True
    elif faction == 'Paradeus':
        faction_folder = output + '/Paradeus护甲'
        for item in fac_ci_xml.iter(tag="carry_item"):
            ci_file = item.attrib["file"]
            ci_folder = faction_folder + '/护甲'
            if REMOVE_OLD and os.path.exists(ci_folder):
                shutil.rmtree(ci_folder)
                REMOVE_OLD = False
            os.makedirs(ci_folder, exist_ok=True)
            parse_ci_file(ci_file, ci_folder)
        logger.info(f"{faction}一共处理了{len(all_ci.keys())}个护甲")
        faction_all_ci[f"{faction}护甲"] = all_ci
        # 要重新生成下一个阵营的文件夹
        REMOVE_OLD = True

def parse_all_carryitem(mod_i_dir:str, all_carryitem_path:str, mod_text_path:str):

    global name2text
    name2text = parse_text(mod_text_path)

    global mod_items_dir
    mod_items_dir = mod_i_dir

    all_ci_xml = et.parse(all_carryitem_path)

    global ci_attrs, cnt, all_ci, faction_all_ci, REMOVE_OLD
    REMOVE_OLD = gval._global_dict["REMOVE_OLD"]
    faction_all_ci = {}

    for item in all_ci_xml.iter(tag="carry_item"):
        xml_file = item.attrib["file"]
        if xml_file.endswith('.xml'):
            all_ci = {}
            ci_attrs = {}
            parse_faction_ci(xml_file)
    cnt = 0
    for k, v in faction_all_ci.items():
        write_weapon_txt(v)

    return faction_all_ci, CARRY_PARAMS


def write_weapon_txt(state_dict: dict):
    DO_WRITE_TXT = gval._global_dict["DO_WRITE_TXT"]
    if not DO_WRITE_TXT:
        return

    def write_one(ci_attrs: dict = None,
                  output_file: str = None,
                  text: str = None,
                  name: str = None,):
        global cnt

        logger.debug(f"正在写入{os.path.basename(output_file)}的文件")
        cnt += 1
        logger.info(f"第{cnt}个护甲：写入{output_file}")

        f = open(output_file, 'w', encoding='utf-8')
        # 名字里不能带 # < > [ ] | { }，并且不要在标题处使用“特殊："
        text = text.replace("-[", "(").replace("]", ")").replace(" [", "(").replace("[", "(").replace("_", " ")
        name = name.replace("-[", "(").replace("]", ")").replace(" [", "(").replace("[", "(").replace("_", " ")
        txt = f"中文名：{text}\n英文名：{name}\n"
        txt += "{{护甲模板ForThwh\n"
        for k in CARRY_PARAMS:
            txt += f"|{k}={ci_attrs[k]}\n"
        txt += "}}\n"

        f.write(txt)
        f.close()

    for k in state_dict.keys():
        write_one(**state_dict[k])

def make_excel(output: str = 'output/carryitem'):
    def enum_keys(type_folder):
        keys = []
        for file in os.scandir(type_folder):
            if file.is_file():
                keys.append(file.name.replace('.txt', ''))
        return keys

    def enum_wtype(faction_folder):
        keys = []
        for wtype in os.scandir(faction_folder):
            if wtype.is_dir():
                keys.extend(enum_keys(wtype.path))
        return keys

    xlsx_path = output + '/护甲数据汇总.xlsx'
    writer = pd.ExcelWriter(xlsx_path)
    workbook = writer.book

    faction_dict = {}
    for item in os.scandir(output):
        if item.is_dir():
            faction_name = item.name
            faction_dict[faction_name] = {"list": []}
            max_len = 0
            for k in enum_wtype(item.path):
                ci_attrs = faction_all_ci[faction_name][k]
                ci_attr = ci_attrs['ci_attrs']
                ci_attr.pop('所属')
                ci_attr.pop('图片名称')
                ci_attr["护甲名称"] = ci_attrs["text"]
                max_len = len(ci_attrs["text"]) if len(
                    ci_attrs["text"]) > max_len else max_len
                faction_dict[faction_name]["list"].append(ci_attr)
            column = CARRY_PARAMS.copy()
            column.insert(0, "护甲名称")
            column.remove('所属')
            column.remove('页面分类')
            column.remove('图片名称')
            faction_dict[faction_name]["col"] = column
            faction_dict[faction_name]["max_len"] = max_len

    for f, d in faction_dict.items():
        df = pd.DataFrame(d["list"], columns=d["col"])
        df.index = df.index + 1
        df.to_excel(writer, f)

        worksheet = writer.sheets[f]
        cell_format = workbook.add_format({
            "align": "left",
            "valign": "vcenter",
        })
        cell_format.set_text_wrap()
        for i, c in enumerate(d["col"]):
            if c == '护甲名称':
                width = d["max_len"]
            else:
                width = len(c) * 2
            worksheet.set_column(i + 1, i + 1, width, cell_format=cell_format)

    writer.save()
    logger.info("表格生成完毕")

