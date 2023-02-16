# Wiki-Generator

## 功能

- 分析武器文件，提取数据生成wiki模板“武器模板ForThwh”格式的文件
- 分析护甲文件，提取数据生成wiki模板“护甲模板ForThwh”格式的文件
- 将提取出的数据制成Excel表格

## 使用

修改 `auto_wiki_generator_thwh.py` 中约 270行左右 `if __name__ == "__main__":` 以后的 `mod_text_path, mod_weapon_dir, mod_items_dir, mod_vehicles_dir` 为自己电脑上的路径，之后运行即可。