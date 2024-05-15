import os
import traceback
from loguru import logger
import pandas as pd
import shutil
import re
from time import sleep
from .parse_weapon import CastlingMeta, WeaponAttr
from typing import Dict
from collections import defaultdict

from time import strftime, localtime
import sys
sys.path.insert(0, sys.path[0] + "/../../")
from utils.misc_func import *


class HuijiWriter:
    def __init__(self, output_dp) -> None:
        self.output_dp = output_dp

    def check_headers(self, temp_fp: str) -> bool:
        self.temp_headers = []
        flag = True
        not_supported = []
        supported = CastlingMeta.supported_header.copy()
        with open(temp_fp, "r", encoding="utf-8") as f:
            txt = f.read()
            matches = re.findall("\|(.*)=", txt)
            for header in matches:
                logger.debug(f"Checking header {header}")
                if header is None or not header:
                    logger.error("模板文件不合法")
                    flag = False
                if header not in supported:
                    not_supported.append(header)
                    flag = False
                else:
                    supported.remove(header)
                self.temp_headers.append(header)

        if len(not_supported) > 0:
            logger.error("{} 尚不支持".format(", ".join(not_supported)))
        if len(supported) > 0:
            logger.info("{} 是额外支持的".format(", ".join(supported)))
        return flag

    def write_weapon_txt(self, key2attr: Dict[str, WeaponAttr]):
        self.cnt = 0
        self.remade_dirs = []
        for key, attr in key2attr.items():
            title2attr = {}
            next_key = attr.next_key
            if next_key is not None:
                next_attr = key2attr[next_key]
                if next_attr.zh_title in title2attr.keys():
                    logger.error(f"{next_key}存在相同的标题:{next_attr.zh_title}")
                    exit(0)
            self.write_one(attr)

    def write_one(self, weapon_attr: WeaponAttr = None):
        output_dp = os.path.join(self.output_dp, weapon_attr.output_subdp)
        if output_dp not in self.remade_dirs:
            if os.path.exists(output_dp):
                shutil.rmtree(output_dp)
            os.makedirs(output_dp)
            self.remade_dirs.append(output_dp)
        output_fp = os.path.join(output_dp, weapon_attr.key)
        self.cnt += 1
        logger.info(f"第{self.cnt}个武器：写入{output_fp}")

        f = open(output_fp, "w", encoding="utf-8")
        # 名字里不能带 # < > [ ] | { }，并且不要在标题处使用“特殊："
        # paires = [["-[", "("], [" [", "("], ["[", "("], ["]", ")"], ["_", " "]]
        # for p in paires:
        #     zh_title = weapon_attr.title["zh"].replace(p[0], p[1])
        #     en_tiel = weapon_attr.title["en"].replace(p[0], p[1])
        txt = f"{weapon_attr.zh_title}\n{weapon_attr.en_title}\n"
        txt += "{{武器\n"
        for k in CastlingMeta.supported_header:
            txt += f"|{k}={weapon_attr[k]}\n"
        txt += "}}\n"

        f.write(txt)
        f.close()
    
    def make_new_excel(self, key2attr: Dict[str, WeaponAttr]):
        headers = ["模板名"] + self.temp_headers
        xlsx_path = os.path.join(self.output_dp, "灰机wiki数据汇总 {}.xlsx".format(strftime('%Y%m%d%H%M',localtime())))
        opened = False
        while not opened:
            try:
                writer = pd.ExcelWriter(xlsx_path)
                opened = True
            except Exception as e:
                logger.error(traceback.format_exc())
                sleep(2)
        workbook = writer.book

        workbook_dict = defaultdict(list)
        sheet2maxlen = {}
        for key, attr in key2attr.items():
            tmp_list = attr.to_excel_row(headers)
            sheet_name = attr.sheet_name
            workbook_dict[sheet_name].append(tmp_list)
            if sheet_name not in sheet2maxlen.keys():
                sheet2maxlen[sheet_name] = [0] * len(headers)
            col_max_len = sheet2maxlen[sheet_name]
            for i, v in enumerate(tmp_list):
                col_max_len[i] = max(col_max_len[i], real_len(str(v)), real_len(headers[i]))

        for sheet_name, row_list in workbook_dict.items():
            df = pd.DataFrame(row_list, columns=headers)
            df.index = df.index + 1
            df.to_excel(writer, sheet_name, index=False)

            worksheet = writer.sheets[sheet_name]
            cell_format = workbook.add_format(
                {
                    "align": "left",
                    "valign": "vcenter",
                }
            )
            cell_format.set_text_wrap()
            col_max_len = sheet2maxlen[sheet_name]
            for i, c in enumerate(headers):
                # if c.endswith("名称"):
                #     width = col_max_len[i] + 2
                # elif c == "炮塔描述":
                #     width = len(c) * 16
                # else:
                #     width = len(c) * 2
                width = col_max_len[i] + 2
                worksheet.set_column(i, i, width, cell_format=cell_format)
            worksheet.freeze_panes(1, 0)
            worksheet.autofilter(0, 0, df.shape[0], df.shape[1] - 1)

        writer.save()
        logger.info(f"{xlsx_path}表格生成完毕")

    def make_excel(self, factions_weapons: Dict[str, Dict[str, WeaponAttr]]):
        def enum_keys(type_folder):
            keys = []
            for file in os.scandir(type_folder):
                if file.is_file():
                    keys.append(file.name.replace(".txt", ""))
            return keys

        def enum_type(faction_folder):
            keys = []
            for wtype in os.scandir(faction_folder):
                if wtype.is_dir():
                    keys.extend(enum_keys(wtype.path))
            return keys

        xlsx_path = self.output_dp + "/武器护甲载具数据汇总.xlsx"
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
        for item in os.scandir(self.output_dp):
            if item.is_dir():
                sheet_name = item.name
                workbook_dict[sheet_name] = {"list": []}
                name_max_len = 0

                if item.name.endswith("武器"):
                    for k in enum_type(item.path):
                        w_attr = factions_weapons[sheet_name][k]
                        w_attr.pop("所属")
                        w_attr.pop("图片名称")
                        w_attr["武器名称"] = w_attrs["text"]
                        name_max_len = (
                            len(w_attrs["text"])
                            if len(w_attrs["text"]) > name_max_len
                            else name_max_len
                        )
                        workbook_dict[sheet_name]["list"].append(w_attr)
                    column = CastlingMeta.supported_header.copy()
                    column.insert(1, "武器名称")
                    column.remove("所属")
                    column.remove("图片名称")

        for f, d in workbook_dict.items():
            df = pd.DataFrame(d["list"], columns=d["columns"])
            df.index = df.index + 1
            df.to_excel(writer, f, index=False)

            worksheet = writer.sheets[f]
            cell_format = workbook.add_format(
                {
                    "align": "left",
                    "valign": "vcenter",
                }
            )
            cell_format.set_text_wrap()
            for i, c in enumerate(d["columns"]):
                if c.endswith("名称"):
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
