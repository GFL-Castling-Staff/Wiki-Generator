import xml.etree.ElementTree as et
from typing import List

def get_hasAttribute(spec: et.Element, attrname: str, default: str = ""):
    if attrname in spec.attrib.keys():
        return spec.attrib[attrname]
    else:
        return default


def recur_get_elements(root:et.ElementTree, tag:str) -> List[et.ElementTree]:
    ret = []
    for ele in root.iter(tag):
        if "file" in ele.attrib.keys():
            ret.extend(recur_get_elements(ele, tag))
        else:
            ret.append(ele)
    return ret

def real_len(s:str):
    # a = len("你好，世界！")
    # a = len("你好，世界！".encode('utf-8'))
    # print(a)
    return len(s.encode('utf-8'))