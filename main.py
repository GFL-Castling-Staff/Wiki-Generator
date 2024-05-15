from loguru import logger
from src import CastlingParser


if __name__ == "__main__":
    logger.add("output/wiki_worker_log.txt",
               encoding="utf-8",
               level="INFO",
               retention="1 minutes")
    mod_root_dp = r"E:\SteamLibrary\steamapps\workshop\content\270150\2606099273\media\packages\GFL_Castling"
    temp_fp = r"conf\huijiwiki.txt"
    parser = CastlingParser(mod_root_dp)
    parser.parse_entry()
    # parser.write_template(temp_fp)
    parser.write_excel(temp_fp)