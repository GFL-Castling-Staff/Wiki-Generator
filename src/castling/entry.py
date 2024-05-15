import os
import xml.etree.ElementTree as et
import re
import sys

from .writer import HuijiWriter
from .parse_weapon import WeaponAttr, WeaponParser

sys.path.insert(0, sys.path[0] + "/../../")
from utils.translator import Translator
from utils.misc_func import *

from enum import Enum, auto, unique

from loguru import logger


@unique
class Faction(Enum):
    GK = 0
    SF = 1
    KCCO = 2
    PARA = 3
    MAX = auto()


class CastlingParser:
    key2attr = {}
    key_has_skill = []

    def __init__(self, mod_root_dp) -> None:
        self.mod_root_dp = mod_root_dp
        self.mod_weapon_dp = os.path.join(mod_root_dp, "weapons")
        self.mod_text_path = os.path.join(
            mod_root_dp, "languages", "cn", "misc_text.xml"
        )
        self.all_weapon_fp = os.path.join(self.mod_weapon_dp, "all_weapons.xml")
        self.skill_as_fp = os.path.join(
            self.mod_root_dp, "scripts", "core", "command_skill_info.as"
        )
        self.writer = HuijiWriter(os.path.join("log", "output"))
        self.faction2function = {
            Faction.GK: self.__parse_GK_weapons,
            Faction.SF: None,
            Faction.KCCO: None,
            Faction.PARA: None,
        }
        real_len("")

    def __parse_translation(self):
        name2text = {}
        # 读取翻译
        if len(self.mod_text_path) != 0:
            root = et.parse(self.mod_text_path)
            for elem in recur_get_elements(root, "text"):
                key = elem.attrib["key"]
                text = elem.attrib["text"]
                name2text[key] = text
            self.__translator = Translator(name2text)

    def __parse_skillkeys(self):
        with open(self.skill_as_fp, "r", encoding="utf-8") as f:
            txt = f.read()
            keys = re.findall('"(.*)"', txt)
            for key in keys:
                self.key_has_skill.append(key)

    def parse_entry(self):
        self.__parse_translation()
        self.__parse_skillkeys()

        self.weapon_parser = WeaponParser(self.mod_weapon_dp, self.__translator)

        all_weapon_xml = et.parse(self.all_weapon_fp)

        for node in all_weapon_xml.iter(tag="weapon"):
            self.__parse_faction_weapon(node.attrib["file"])

    def write_template(self, temp_fp: str):
        if self.writer.check_headers(temp_fp):
            self.writer.write_weapon_txt(self.key2attr)

    def write_excel(self, temp_fp: str):
        if self.writer.check_headers(temp_fp):
            self.writer.make_new_excel(self.key2attr)

    def __parse_faction_weapon(self, faction_weapons_fn: str):
        # 匹配阵营
        if faction_weapons_fn.startswith("gk"):
            faction = Faction.GK
        elif faction_weapons_fn.startswith("sf"):
            faction = Faction.SF
        elif faction_weapons_fn.startswith("kcco"):
            faction = Faction.KCCO
        elif faction_weapons_fn.startswith("paradeus"):
            faction = Faction.PARA
        else:
            return

        logger.info(f"正在解析{faction}的武器文件{faction_weapons_fn}")

        faction_weapons_fp = os.path.join(self.mod_weapon_dp, faction_weapons_fn)

        func = self.faction2function[faction]
        if func is not None:
            func(faction_weapons_fp)
        # if faction == Faction.GK:
        #     # 读取gk_weapons.xml里的条目
        #     if not in_rec:
        #         logger.info(f"{faction}一共处理了{len(keys_weaponinfos.keys())}把武器")
        #         factions_weapons[f"{faction}武器"] = keys_weaponinfos
        # elif faction == "SF":
        #     faction_folder = output + "/SF武器"
        #     if REMOVE_OLD and os.path.exists(faction_folder):
        #         shutil.rmtree(faction_folder)
        #     # 读取sf_weapons.xml里的条目
        #     for node in faction_weapons_ett.iter(tag="weapon"):
        #         weapon_file = node.attrib["file"]
        #         weapon_folder = faction_folder + f"/武器"
        #         os.makedirs(weapon_folder, exist_ok=True)

        #         weapon_attrs["武器编号"] = ""
        #         weapon_attrs["页面分类"] = "SF武器"
        #         parse_weapon_file(weapon_file, weapon_folder)
        #     if not in_rec:
        #         logger.info(f"{faction}一共处理了{len(keys_weaponinfos.keys())}把武器")
        #         factions_weapons[f"{faction}武器"] = keys_weaponinfos
        # elif faction == "KCCO":
        #     faction_folder = output + "/KCCO武器"
        #     if REMOVE_OLD and os.path.exists(faction_folder):
        #         shutil.rmtree(faction_folder)
        #     # 读取kcco_weapons.xml里的条目
        #     for node in faction_weapons_ett.iter(tag="weapon"):
        #         weapon_file = node.attrib["file"]
        #         # 不好处理
        #         unhandlable = ["othrusdog", "dactyl"]
        #         pass_this = False
        #         for u in unhandlable:
        #             if u in weapon_file:
        #                 pass_this = True
        #                 break
        #         if pass_this:
        #             logger.warning(f"跳过{weapon_file}的处理")
        #             continue
        #         weapon_folder = faction_folder + f"/武器"
        #         os.makedirs(weapon_folder, exist_ok=True)

        #         weapon_attrs["武器编号"] = ""
        #         weapon_attrs["页面分类"] = "KCCO武器"
        #         parse_weapon_file(weapon_file, weapon_folder)
        #     if not in_rec:
        #         logger.info(f"{faction}一共处理了{len(keys_weaponinfos.keys())}把武器")
        #         factions_weapons[f"{faction}武器"] = keys_weaponinfos
        # elif faction == "Paradeus":
        #     faction_folder = output + "/Paradeus武器"
        #     if REMOVE_OLD and os.path.exists(faction_folder):
        #         shutil.rmtree(faction_folder)
        #     # 读取paradeus_weapons.xml里的条目
        #     for node in faction_weapons_ett.iter(tag="weapon"):
        #         weapon_file = node.attrib["file"]
        #         if weapon_file.startswith("parw") or weapon_file.startswith("eild"):
        #             # 不好处理
        #             unhandlable = ["infected"]
        #             pass_this = False
        #             for u in unhandlable:
        #                 if u in weapon_file:
        #                     pass_this = True
        #                     break
        #             if pass_this:
        #                 logger.warning(f"跳过{weapon_file}的处理")
        #                 continue
        #             weapon_folder = faction_folder + f"/武器"
        #             os.makedirs(weapon_folder, exist_ok=True)

        #             weapon_attrs["武器编号"] = ""
        #             weapon_attrs["页面分类"] = "Paradeus武器"
        #             parse_weapon_file(weapon_file, weapon_folder)
        #     if not in_rec:
        #         logger.info(f"{faction}一共处理了{len(keys_weaponinfos.keys())}把武器")
        #         factions_weapons[f"{faction}武器"] = keys_weaponinfos

    def __parse_GK_weapons(self, faction_weapons_fp: str):
        faction_weapons_ett = et.parse(faction_weapons_fp)

        for node in faction_weapons_ett.iter(tag="weapon"):
            weapon_fn = node.attrib["file"]
            # 匹配gk_weapons.xml里的嵌套武器文件
            weapons_fn_pattern = "gk_weapons_[3a-zA-Z_]+.xml"
            # 这种短正则里面没有编号，真是差不多得了
            weapon_short_fn_pattern = "gkw_((?!MOD3)(?!mod3)[0-9a-zA-Z]+)?.weapon"
            # gkw_编号_类型_弹头_名字
            # gkw_编号_类型_弹头_名字_MOD3
            # 为什么是_only呢？我不明白
            weapon_fn_pattern = "gkw_[0-9]+_((ar)|(smg)|(hg)|(rf)|(sg)|(mg))_[0-9a-zA-Z.-]+_[0-9a-zA-Z.-]+(_(?!MOD3)(?!mod3)[0-9a-zA-Z]+)?(_skill)?(_only)?(_hero)?.weapon"
            weapon_mod3_fn_pattern = "gkw_[0-9]+_((ar)|(smg)|(hg)|(rf)|(sg)|(mg))_[0-9a-zA-Z.-]+_[0-9a-zA-Z.-]+(_[0-9a-zA-Z]+)?((_MOD3)|(_mod3))(_skill)?(_only)?.weapon"
            # 前面两种_skill，以前的老命名文件了
            # 前面两种_皮肤编号_SKIN，以前的老命名文件了
            skin_pattern = "gkw_[0-9]+_((ar)|(smg)|(hg)|(rf)|(sg)|(mg))_[0-9a-zA-Z.-]+_[0-9a-zA-Z.-]+(_(?!MOD3)(?!mod3)[0-9a-zA-Z]+)?_[0-9a-zA-Z]+_SKIN(_skill)?(_only)?(_hero)?.weapon"
            skin_mod3_pattern = "gkw_[0-9]+_((ar)|(smg)|(hg)|(rf)|(sg)|(mg))_[0-9a-zA-Z.-]+_[0-9a-zA-Z.-]+(_[0-9a-zA-Z]+)?((_MOD3)|(_mod3))_[0-9a-zA-Z]+_SKIN(_skill)?(_only)?.weapon"
            # 一些不同命名格式的文件
            special_pattern = (
                "((gkw_special_cyclops)|(target)|(gkw_medical_agl_hg)).weapon"
            )
            # HVY武器
            hvy_pattern = (
                "gkw_((hvy)|(228_smg_8x22_type100_banzai)|(hvypdw))[a-z0-9_]*.weapon"
            )

            if re.match(weapons_fn_pattern, weapon_fn) is not None:
                faction_weapons_fp = os.path.join(
                    os.path.dirname(faction_weapons_fp), weapon_fn
                )
                self.__parse_GK_weapons(faction_weapons_fp)
                continue
            elif weapon_fn.startswith("FF"):
                weapon_attr = WeaponAttr(**{"武器编号": "", "页面分类": "融合势力"})
            elif re.match(hvy_pattern, weapon_fn) is not None:
                weapon_attr = WeaponAttr(**{"武器编号": "", "页面分类": "HVY"})
            elif re.match(special_pattern, weapon_fn) is not None:
                weapon_attr = WeaponAttr(**{"武器编号": "", "页面分类": "特殊武器"})
            else:
                weapon_attr = WeaponAttr()
                if (
                    re.match(weapon_fn_pattern, weapon_fn) is not None
                    # or re.match(weapon_short_fn_pattern, weapon_fn) is not None
                ):
                    weapon_attr.sheet_name = "普通武器"
                elif re.match(weapon_mod3_fn_pattern, weapon_fn) is not None:
                    weapon_attr.sheet_name = "三改武器"
                elif re.match(skin_pattern, weapon_fn) is not None:
                    weapon_attr.sheet_name = "普通皮肤"
                elif re.match(skin_mod3_pattern, weapon_fn) is not None:
                    weapon_attr.sheet_name = "三改皮肤"
                else:
                    logger.warning(f"跳过{weapon_fn}的处理")
                    continue
                s = weapon_fn.split("_")
                weapon_id = int(s[1])
                if weapon_id == 404:
                    # logger.info(f"跳过{weapon_file}的处理")
                    continue
                weapon_type = s[2].upper()
                weapon_attr.add_header(
                    **{"武器编号": weapon_id, "页面分类": f"{weapon_type}"}
                )

            if "mod3" in weapon_fn.lower():
                weapon_attr["武器类型"] = "三改"
                weapon_attr["是否真核"] = "否"
            else:
                weapon_attr["武器类型"] = "普通型"
                weapon_attr["是否真核"] = "是"
            weapon_attr["所属"] = "G&K"
            weapon_attr["获取方式"] = ""
            weapon_attr["是否脚本"] = "是"
            weapon_attr.output_subdp = os.path.join("GK武器", weapon_attr["页面分类"])

            weapon_fp = os.path.join(os.path.dirname(faction_weapons_fp), weapon_fn)
            self.__parse_weapon_file(weapon_fp, weapon_attr)

    def __parse_weapon_file(self, weapon_fp: str, weapon_attr: WeaponAttr):
        weapon_ett = et.parse(weapon_fp)

        weapon_root = weapon_ett.getroot()

        if weapon_root.tag == "weapons":
            for attr in self.weapon_parser.read_weapons(weapon_root, weapon_attr):
                self.__fill_skill_header(attr)
                self.key2attr[attr.key] = attr
        elif weapon_root.tag == "weapon":
            attr = self.weapon_parser.read_weapon(weapon_root, weapon_attr)
            if attr is not None:
                self.__fill_skill_header(attr)
                self.key2attr[attr.key] = attr

    def __fill_skill_header(self, attr: WeaponAttr):
        if attr.key in self.key_has_skill:
            attr["技能有无"] = "有"
        else:
            attr["技能有无"] = "无"
        attr["技能名称"] = ""
        attr["技能效果"] = ""

    def __gen_part_template(params: list, can_empty: list):
        ret = ""
        for p in params:
            if p in can_empty:
                ret += (
                    """|-
    {{#if:{{{"""
                    + p
                    + """|}}}|
    {{!}} """
                    + p
                    + """
    {{!}}colspan=2{{!}}{{{"""
                    + p
                    + """}}}
    }}
    """
                )
            else:
                ret += (
                    """|-
    | """
                    + p
                    + """
    |colspan=2|{{{"""
                    + p
                    + "}}}\n"
                )
        return ret
