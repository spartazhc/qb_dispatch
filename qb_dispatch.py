#!/usr/bin/python3
# this script work as qbittorrent's external program and will
# rename and create hard link for emby/jellyfin to scrape easily
# film and episodes naming rule follows https://jellyfin.org/docs/general/server/media/movies.html
# 2021-01-26 by spartazhc

# Usage: download this python script, setup in qbittorrent
# Option -> Download -> Run external program on torrent completion
# set as /path_of_script/qb_dispatch.py -f "%F" -c "%L" -n "%N"
# Set categories "episodes" and "films", choose them when add torrent
# Note: for non-standard film name, script will fail or mismatch

# 2021-02-02 add country_codes and cut_types, code clean
# 2021-02-23 fix regex for punctuations in film name; better error logging; add episode-chi
# 2021-02-25 use git repository to manage other than gist

import re
import os
import sys
import subprocess
import argparse
import logging
import configparser
import tmdbsimple as tmdb

# bluray source
country_codes = ["BFI", "CEE", "CAN", "CHN", "ESP", "EUR", "FRA", "GBR", "GER", "HKG", "IND", "ITA", "JPN", "KOR", "NOR", "NLD", "POL", "RUS", "TWN", "USA"]
cut_types = { 'cc': 'CC', 'criterion': 'CC', 'director': 'Directors Cut', 'extended': 'Extended Cut', 'uncut': 'UNCUT', 'remastered': 'Remastered', 'repack': 'Repack', 'uncensored': 'Uncensored', 'unrated': 'Unrated'}

def is_video_or_subtitle(fname):
    video_suffix = ["mp4", "mkv", "avi", "wmv", "m2ts", "rmvb", "srt", "ass", "sup"]
    fname = fname.lower()
    for suffix in video_suffix:
        if fname.endswith(suffix):
            return True
    return False

def getname_episodes(ori_name, tmdb_refine, filter_list):
    to_filter = re.sub('S\d{2}-?|E\d{2}|合集|全\d+集|Part\d+-\d+|Complete|AMZN|中英.*CMCT.*', '', ori_name)
    fullname = re.sub(filter_list, '', to_filter)
    match = re.match(u"([\u4E00-\u9FA5]?.*[\u4E00-\u9FA5]+).*", fullname)
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
        if not start_flag and (item[0].isupper() or item[0].isdigit()):
            start_flag = 1
        elif item[0].isdigit() or item[0] == '-' or ("web" in item.lower()) or ("blu" in item.lower()):
            break
        if start_flag:
            name_t.append(item)
    vf_en = ' '.join(name_t)
    # 3. get year
    match = re.search('19\d{2}|20\d{2}', fullname)
    if match:
        year = match[0]
    else:
        year = ""
    logging.debug(f"getname_episodes: zh:{vf_zh}, en:{vf_en}, year:{year}")
    if tmdb_refine:
        # if it is not S01, than du not use year to refine
        match = re.search("S\d{2}", ori_name)
        if match and match[0] != 'S01':
            year = ""
        vf_zh, vf_en, year = refine_episode(vf_zh, vf_en, year)
        logging.debug(f"tmdb_refine: zh:{vf_zh}, en:{vf_en}, year:{year}")
    else:
        logging.debug(f"tmdb_refine: disabled")
    return vf_zh, vf_en, year

# for tv now
def refine_translations(id):
    vf_zh = ''
    vf_en = ''
    tv = tmdb.TV(id=id)
    trans_ret = tv.translations()
    if trans_ret:
        for item in trans_ret['translations']:
            if item['iso_3166_1'] == 'CN' and item['iso_639_1'] == 'zh':
                vf_zh = item['data']['name']
            elif item['iso_3166_1'] == 'US' and item['iso_639_1'] == 'en':
                vf_en = item['data']['name']
            else:
                continue

    return vf_zh, vf_en

def refine_episode(in_zh, in_en, in_year):
    vf_zh , vf_en, year = in_zh, in_en, in_year
    if in_zh:
        search_zh = tmdb.Search()
        search_zh.tv(query=in_zh, first_air_date_year=in_year, language='zh')
        if search_zh.results:
            item = search_zh.results[0]
            if item['original_language'] == 'en':
                vf_en = item['original_name']
            else:
                _, vf_en = refine_translations(item['id'])
            return item['name'], vf_en, item['first_air_date'][:4]
    # no in_zh input or search_zh no results
    search_en = tmdb.Search()
    search_en.tv(query=in_en, first_air_date_year=in_year, language='en')
    if search_en.results:
        # print(search_en.results)
        idx = 0
        for i, item in enumerate(search_en.results):
            # with backdrop and perfect name match
            if item['backdrop_path'] is not None and item['name'] == in_en:
                idx = i
                break
        if idx == 0:
            for i, item in enumerate(search_en.results):
                # first item with backdrop
                if (item['backdrop_path'] is not None):
                    idx = i
                    break
        item = search_en.results[idx]
        year = item['first_air_date'][:4]
        vf_en = item['name']
        if item['original_language'] == "zh":
            vf_zh = item['original_name']
        else:
            vf_zh, _ = refine_translations(item['id'])


    return vf_zh, vf_en, year

def link_episodes(spath, target, linkdir):
    fullname = os.path.basename(spath)
    logging.info(f"'{fullname}' => '{target}'")
    if check:
        print(f"'{fullname}' => '{target}'")
        sys.exit()
    if not target:
        logging.error(f"episodes: no short name on '{fullname}', check!")
        return
    if not os.path.exists(os.path.join(linkdir, target)):
        os.makedirs(os.path.join(linkdir, target))
    # print(spath)
    if os.path.isdir(spath):
        for root, dirs, files in os.walk(spath):
            vfiles = [f for f in files if is_video_or_subtitle(f)]
            # print(vfiles)
            if not vfiles:
                continue
            series_base = os.path.basename(root)
            m = re.match(r".*(S\d+).*", series_base)
            if not m:
                logging.warning(f"episodes: no season number found, regard as only one season.")
                season = "S01"
            else:
                season = m[1]
            season_dir = os.path.join(linkdir, target, season)
            if not os.path.exists(season_dir):
                os.makedirs(season_dir)
            vfiles.sort()
            for vf in vfiles:
                se_str = season
                sp = re.findall(r"(SP[E]?\d*)", vf)
                if not sp:
                    ep_list = re.findall(r"(E[Pp]?\d+)", vf)
                    if not ep_list:
                        logging.warning(f"episodes: check special: {vf}")
                        continue
                    else:
                        for ep in ep_list:
                            se_str += ep
                else:
                    se_str += sp[0]
                link_cmd = f"ln \"{os.path.join(root, vf)}\" \"{os.path.join(season_dir, se_str)}.{vf.split('.')[-1]}\""
                logging.info(f"episodes: link: {link_cmd}")
                try:
                    subprocess.check_output(link_cmd, stderr=subprocess.STDOUT, shell=True)
                except subprocess.CalledProcessError as e:
                    logging.error(f"episodes: link: {e.output}")

def dispatch_episodes(path, linkdir, lang, tmdb_refine, filter_list):
    fname = os.path.basename(path)
    vf_zh, vf_en, year = getname_episodes(fname, tmdb_refine, filter_list)
    if lang == 'zh' and vf_zh != "":
        vf = f"{vf_zh}" if not year else f"{vf_zh} ({year})"
    else:
        vf = f"{vf_en}" if not year else f"{vf_en} ({year})"
    link_episodes(path, vf, linkdir)

def link_film(vf, root, linkdir, filter_list):
    vf_ori = os.path.basename(vf)
    vf_ori = re.sub(filter_list, "", vf_ori)
    vf_ori = re.sub("\[.*\]|IMAX", "", vf_ori)
    # Remove Chinese
    vf_en = re.sub("[\u4E00-\u9FA5]+.*[\u4E00-\u9FA5]+.*?\.", "", vf_ori)
    logging.debug(f'vf_en after filter: "{vf_en}"')
    m = re.match(r"\.?([\w,.'!?&-]+)\.(\d{4})+.*(720[pP]|1080[pP]|2160[pP])+.*(mkv|mp4|m2ts|srt|ass)+", vf_en)
    # TODO: deal with extra videos
    if "EXTRA" in vf_en or "FEATURETTE" in vf_en or "Sample" in vf_en or "sample" in vf_en:
        return
    cut = ""
    country = ""
    # check FIFA country code
    for code in  country_codes:
        if code in vf_en:
            country = code
            break
    vf_en_lower = vf_en.lower()
    for key, val in cut_types.items():
        if key in vf_en_lower:
            cut = val
            break
    # Normally, there should be either country or cut
    cut = country + cut
    if m is None:
        # sometimes there is no resolution in filename, maybe the uploader missed it
        m = re.match(r"([\w,.'!?&-]+).(\d{4})+.*(mkv|mp4|m2ts|srt|ass)+", vf_en)
        if m is None:
            print(f"vf_en: {vf_en}, fail in regex match")
            logging.error(f"vf_en: {vf_en}, fail in regex match")
            return
        name, year, reso, suffix = m[1], m[2], "1080p", m[3]
        if "AKA" in m[1]:
            try:
                name = re.match(r"([\w,.'!?&-]+)\.AKA.*", m[1])[1]
            except TypeError:
                print(f"vf_en: {vf_en}, fail in AKA regex match")
                logging.error(f"vf_en: {vf_en}, fail in AKA regex match")
        fname = f"{name.replace('.', ' ')} ({year}) - [{cut if cut else reso}].{suffix}"
        logging.warning(f"no resolution found, set as 1080p.")
    else:
        name, year, reso, suffix = m[1], m[2], m[3].lower(), m[4]
        if "AKA" in m[1]:
            try:
                name = re.match(r"([\w,.'!?&-]+)\.AKA.*", m[1])[1]
            except TypeError:
                print(f"vf_en: {vf_en}, fail in AKA2 regex match")
                logging.error(f"vf_en: {vf_en}, fail in AKA2 regex match")
        fname = f"{name.replace('.', ' ')} ({year}) - [{cut if cut else reso}].{suffix}"

    vf_dir = os.path.join(linkdir, f"{name.replace('.', ' ')} ({year})")
    if not os.path.exists(vf_dir):
        os.makedirs(vf_dir)
    link_cmd = f"ln \"{os.path.join(root, vf)}\" \"{vf_dir}/{fname}\""
    if check:
        print(link_cmd)
        sys.exit()
    if os.path.exists(f"{vf_dir}/{fname}"):
        logging.error(f"films: check: file already exists \"{vf_dir}/{fname}\"")
        return
    logging.info(f"films: cmd: {link_cmd}")
    try:
        subprocess.check_output(link_cmd, stderr=subprocess.STDOUT, shell=True)
    except subprocess.CalledProcessError as e:
        logging.error(f"films: link: {e.output}")

def dispatch_films(path, linkdir, filter_list):
    if not os.path.isdir(path) and is_video_or_subtitle(path):
        link_film(path, "", linkdir, filter_list)
    for root, dirs, files in os.walk(path):
        vfiles = [f for f in files if is_video_or_subtitle(f)]
        if not vfiles:
            continue
        for vf in vfiles:
            link_film(vf, root, linkdir, filter_list)

check = False
if __name__ == '__main__':
    pwd = os.path.dirname(os.path.realpath(__file__))
    parser = argparse.ArgumentParser(
        description='qbittorrent download file dispatcher for nas')
    parser.add_argument('-f', "--file", required=True,
                        help="content path (root path for multifile torrent")
    parser.add_argument('-c', "--category", required=True,
                        help="torrent category")
    parser.add_argument("--config", default=os.path.join(pwd, "config.ini"),
                        help="config file")
    parser.add_argument('-n', "--name",
                        help="torrent name")
    parser.add_argument('--check', action='store_true',
                        help="just check output, not do")
    args = parser.parse_args()
    if args.check:
        check=True
    # read config
    config = configparser.ConfigParser()
    config.read(args.config)
    if config['default']['tmdb-refine'] == 'yes':
        tmdb.API_KEY = config['default']['tmdb-apikey']
        tmdb_refine = True
    else:
        tmdb_refine = False
    logging.basicConfig(filename=os.path.join(pwd, config['default']['logpath']),
                        format='%(asctime)-15s %(levelname)s %(message)s',
                        level=logging.getLevelName(config['default']['loglevel']))
    ifile = args.file
    # path replacement
    for substr in config['docker-path-replacement']:
        if substr in args.file:
            ifile = args.file.replace(substr, config['docker-path-replacement'][substr])
            break

    for cate in config['film-link-binding']:
        if args.category == cate:
            dispatch_films(ifile, config['film-link-binding'][cate], config['filter-list']['films'])
            sys.exit()

    for cate in config['episode-link-binding']:
        if args.category == cate:
            dispatch_episodes(ifile, config['episode-link-binding'][cate], config['default']['language'], tmdb_refine, config['filter-list']['episodes'])
            sys.exit()
