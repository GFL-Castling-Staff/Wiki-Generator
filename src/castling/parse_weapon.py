from loguru import logger
import xml.etree.ElementTree as et
import re
import os
from utils.misc_func import *
import copy
import sys

sys.path.insert(0, sys.path[0] + "/../../")
from utils.translator import Translator


class CastlingMeta:
    supported_header = [
        "页面分类",
        "弹头类型",
        "伤害类型",
        "致死/伤害",
        "绝对追伤",
        "是否消音",
        "移动速度修改量",
        "被发现率修改量",
        "抗致死性修改量",
        "弹匣容量",
        "单次上弹数",
        "弹速",
        "自动化程度",
        "单次击发弹丸抛射量",
        "单次射击连续击发次数",
        "单次击发间隔",
        "连续击发每两次击发间隔",
        "视距",
        "衰减开始时间",
        "衰减开始距离",
        "衰减结束时间",
        "衰减结束距离",
        "散步范围",
        "初始精准度",
        "后坐力增长率",
        "后坐力回复率",
        "所属",
        "图片名称",
        "武器编号",
        "过热阈值",
        "过热结束阈值",
        "武器类型",
        "获取方式",
        "是否真核",
        "是否脚本",
        "技能有无",
        "技能名称",
        "技能效果",
    ]


class WeaponAttr(dict):
    zh_title = ""
    en_title = ""
    key = ""
    next_key = None
    output_subdp = ""
    sheet_name = ""

    def __init__(self, **kwargs) -> None:
        super().__init__(kwargs)
        # self.__mapper.update(**kwargs)

    def add_header(self, **kwargs):
        self.update(**kwargs)

    def fill_headers(self):
        keys = CastlingMeta.supported_header[:]
        for k in self.keys():
            if k not in keys:
                logger.info(f"{k} 尚未添加到supported_header")
                exit(0)
            else:
                keys.remove(k)

        # 因为这个逼游戏，缺失一些元素也是可以运行的
        # 所以不再抛出错误，而是全部设置为空
        if len(keys) != 0:
            err = "These keys are not defined: "
            for k in keys:
                # err += f"{' '*4}{k}\n"
                self[k] = ""
            err += ", ".join(keys)
            logger.warning(err)
            # raise ValueError(err)
        else:
            logger.debug("All keys are defined")

    def to_excel_row(self, keys: List[str]):
        ret = []
        for k in keys:
            if k == "模板名":
                keys[0] = "武器"
                ret.append(self.zh_title)
            elif k == "武器":
                ret.append(self.zh_title)
            else:
                ret.append(self[k])
        return ret


class WeaponParser:
    def __init__(self, mod_weapon_dp: str, translator: Translator) -> None:
        self.__mod_weapon_dp = mod_weapon_dp
        self.__translator = translator

    def read_weapons(
        self, weapons: et.Element, weapon_attr: WeaponAttr
    ) -> List[WeaponAttr]:
        ret = []
        for wp in weapons.findall("weapon"):
            copy_weapon_attr = self.read_weapon(wp, weapon_attr)
            if copy_weapon_attr is not None:
                ret.append(copy_weapon_attr)
                if len(ret) > 1:
                    ret[-2].next_key = ret[-1].key
        return ret

    def read_weapon(
        self, weapon: et.Element, raw_weapon_attr: WeaponAttr
    ) -> WeaponAttr:
        weapon_attr = copy.deepcopy(raw_weapon_attr)

        # 过滤key值
        key = weapon.attrib["key"]
        if "_ai" in key or "AI" in key:
            return None

        weapon_attr.key = key

        # 读取specification中的数据
        specification = weapon.find("specification")
        self.__read_specification(specification, weapon_attr)

        # 读取弹头中的数据
        projectile = weapon.find("projectile")
        self.__read_projectile(projectile, weapon_attr)

        # 读取Hud名字
        hud = weapon.find("hud_icon")
        weapon_attr["图片名称"] = get_hasAttribute(hud, "filename")

        # 读取modifier
        modifier = weapon.findall("modifier")
        speed = 0
        detectability = 0
        hit_success_probability = 0

        for i in modifier:
            modifierClass = get_hasAttribute(i, "class")
            if modifierClass == "speed":
                speed = i.attrib["value"]
            elif modifierClass == "detectability":
                detectability = i.attrib["value"]
            elif modifierClass == "hit_success_probability":
                hit_success_probability = i.attrib["value"]
            else:
                continue
        weapon_attr["移动速度修改量"] = speed
        weapon_attr["被发现率修改量"] = detectability
        weapon_attr["抗致死性修改量"] = -float(hit_success_probability)

        weapon_attr.fill_headers()

        for k, v in weapon_attr.items():
            if isinstance(v, str):
                try:
                    weapon_attr[k] = float(v)
                except:
                    continue

        return weapon_attr

    def __read_specification(self, spec: et.Element, weapon_attr: WeaponAttr):
        # 1
        weapon_attr["单次击发间隔"] = get_hasAttribute(spec, "retrigger_time", "-1")

        # 2
        weapon_class = get_hasAttribute(spec, "class", "0")
        if weapon_class == "0":
            weapon_class = "全自动"
        elif weapon_class == "1":
            weapon_class = "手动"
        elif weapon_class == "2":
            weapon_class = "手动"
        elif weapon_class == "3":
            weapon_class = "不显示弹药"
        elif weapon_class == "4":
            weapon_class = "半自动"
        elif weapon_class == "5":
            weapon_class = "消耗物/部署物"
        else:
            weapon_class = "N/A"
        weapon_attr["自动化程度"] = weapon_class

        # 3
        weapon_attr["初始精准度"] = get_hasAttribute(spec, "accuracy_factor", 1)

        # 4
        weapon_attr["单次击发弹丸抛射量"] = get_hasAttribute(
            spec, "projectiles_per_shot", 1
        )

        # 5
        weapon_attr["单次射击连续击发次数"] = get_hasAttribute(spec, "burst_shots", 1)

        # 6
        weapon_attr["连续击发每两次击发间隔"] = get_hasAttribute(
            spec, "last_burst_retrigger_time"
        )

        # 7
        weapon_attr["后坐力增长率"] = get_hasAttribute(spec, "sustained_fire_grow_step")

        # 8
        weapon_attr["后坐力回复率"] = get_hasAttribute(
            spec, "sustained_fire_diminish_rate"
        )

        # 9
        weapon_attr["弹匣容量"] = spec.attrib["magazine_size"]

        # 10
        # 如果reload_one_at_a_time为0或者它不存在都是一次性装满
        # 如果为1则要看动画才能知道，交给写wiki的人填
        value = get_hasAttribute(spec, "reload_one_at_a_time", "0")
        weapon_attr["单次上弹数"] = (
            weapon_attr["弹匣容量"] if value == "0" else "Unknown"
        )

        # 10
        weapon_attr["视距"] = get_hasAttribute(spec, "sight_range_modifier", 1)

        # 11
        weapon_attr["散步范围"] = get_hasAttribute(spec, "spread_range")

        # 12
        suppressed = get_hasAttribute(spec, "suppressed", "0")
        weapon_attr["是否消音"] = "是" if suppressed == "1" else "否"

        # 13
        weapon_attr["弹速"] = get_hasAttribute(spec, "projectile_speed")

        # 14
        weapon_attr["过热阈值"] = get_hasAttribute(spec, "cooldown_start")
        weapon_attr["过热结束阈值"] = get_hasAttribute(spec, "cooldown_end")

        weapon_attr.zh_title = self.__translator.get(spec.attrib["name"])
        weapon_attr.en_title = self.__translator.get(spec.attrib["name"])

    def __read_projectile(self, proj: et.Element, weapon_attr: WeaponAttr):
        if proj != None:
            result = proj.find("result")
            if result != None:
                self.__read_result(result, weapon_attr)
            else:
                projectile_fn = proj.attrib["file"]
                projectile_fp = os.path.join(self.__mod_weapon_dp, projectile_fn)
                projectile_ett = et.parse(projectile_fp)
                result = projectile_ett.find("result")
                if result != None:
                    self.__read_result(result, weapon_attr)
                else:
                    logger.warning("Cant get projectile <result> tag")
                    # raise ValueError("Cant get projectile <result> tag")
        else:
            logger.warning("Projectile is none")
            # raise ValueError("Projectile is none")

    def __read_result(self, result: et.Element, weapon_attr: dict):
        projectile_class = result.attrib["class"]
        if projectile_class == "hit":
            projectile_class = "动能"
            weapon_attr["致死/伤害"] = get_hasAttribute(result, "kill_probability")
        elif projectile_class == "blast":
            projectile_class = "爆炸"
            weapon_attr["致死/伤害"] = get_hasAttribute(result, "damage")
        elif projectile_class == "notify_script":
            projectile_class = "脚本"
        elif projectile_class == "spawn":
            projectile_class = "子母弹"
        else:
            raise ValueError(f"projectile_class: {projectile_class} is not defined")

        weapon_attr["弹头类型"] = projectile_class

        damage_cls = get_hasAttribute(result, "character_state")
        if damage_cls == "unwound":
            damage_cls = "治疗"
        elif damage_cls == "":
            damage_cls = "death"
        weapon_attr["伤害类型"] = damage_cls

        weapon_attr["绝对追伤"] = get_hasAttribute(
            result, "kill_probability_offset_on_successful_hit"
        )

        stime = get_hasAttribute(result, "kill_decay_start_time")
        weapon_attr["衰减开始时间"] = stime

        etime = get_hasAttribute(result, "kill_decay_end_time")
        weapon_attr["衰减结束时间"] = etime

        if weapon_attr["弹速"] == "":
            sdistance = ""
            edistance = ""
        else:
            if stime != "":
                sdistance = float(stime) * float(weapon_attr["弹速"])
            else:
                sdistance = ""
            if etime != "":
                edistance = float(etime) * float(weapon_attr["弹速"])
            else:
                edistance = ""

        weapon_attr["衰减开始距离"] = sdistance
        weapon_attr["衰减结束距离"] = edistance
