
import re

def getname_episodes(fullname):
    fullname = re.sub('S\d{2}|E\d{2}|合集|全\d+集|Part\d+-\d+|Complete|AMZN', '', fullname)
    match = re.match(u"([\u4E00-\u9FA5]+.*[\u4E00-\u9FA5]+).*", fullname)
    # 1. get chinese name
    if match:
        vf_zh = match[1].replace('.', ' ')
    else:
        vf_zh = ""
    # 2. get english name
    fs = fullname.split('.')
    name_t = []
    start_flag = 0
    for item in fs:
        if not item:
            continue
        if not start_flag and not (item[0].isupper() or item[0].isdigit()):
            continue
        elif item[0].isdigit() or item[0] == '-' or ("web" in item.lower()) or ("blu" in item.lower()):
            break
        name_t.append(item)
        start_flag = 1
    vf_en = ' '.join(name_t)
    # 3. get year
    match = re.search('19|20\d{2}', fullname)
    if match:
        year = match[0]
    else:
        year = ""
    return vf_zh, vf_en, year