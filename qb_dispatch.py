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

# bluray source
country_codes = ["BFI", "CEE", "CAN", "CHN", "ESP", "EUR", "FRA", "GBR", "GER", "HKG", "IND", "ITA", "JPN", "KOR", "NOR", "NLD", "POL", "RUS", "TWN", "USA"]
cut_types = { 'cc': 'CC', 'criterion': 'CC', 'director': 'Directors Cut', 'extended': 'Extended Cut', 'uncut': 'UNCUT', 'remastered': 'Remastered', 'repack': 'Repack', 'uncensored': 'Uncensored', 'unrated': 'Unrated'}

def is_video_or_subtitle(fname):
    video_suffix = ["mp4", "mkv", "avi", "wmv", "m2ts", "rmvb", "srt", "ass"]
    fname = fname.lower()
    for suffix in video_suffix:
        if fname.endswith(suffix):
            return True
    return False

def link_episodes(spath, target, linkdir):
    fullname = os.path.basename(spath)
    logging.info(f"'{fullname}' => '{target}'")
    if not target:
        logging.error(f"episodes: no short name on '{fullname}', check!")
        return
    if not os.path.exists(os.path.join(linkdir, target)):
        os.makedirs(os.path.join(linkdir, target))
    if os.path.isdir(spath):
        for root, dirs, files in os.walk(spath):
            vfiles = [f for f in files if is_video_or_subtitle(f)]
            if not vfiles:
                continue
            series_base = os.path.basename(root)
            m = re.match(r".*(S\d+).*", series_base)
            if not m:
                logging.warning(f"episodes: no season number found, regard as only one season.")
                season = ""
            else:
                season = m[1]
            season_dir = os.path.join(linkdir, target, season)
            if not os.path.exists(season_dir):
                os.makedirs(season_dir)
            vfiles.sort()
            for vf in vfiles:
                m = re.match(r".*(S\d{2}E\d+).*", vf)
                if not m:
                    m2 = re.match(r".*(E[p]?\d+).*", vf)
                    if not m2:
                        logging.warning(f"episodes: check special: {vf}")
                        continue
                    else:
                        se_str = m2[1]
                else:
                    se_str = m[1]
                link_cmd = f"ln \"{os.path.join(root, vf)}\" \"{os.path.join(season_dir, se_str)}.{vf.split('.')[-1]}\""
                logging.info(f"episodes: link: {link_cmd}")
                try:
                    subprocess.check_output(link_cmd, stderr=subprocess.STDOUT, shell=True)
                except subprocess.CalledProcessError as e:
                    logging.error(f"episodes: link: {e.output}")

def getname_episodes(fullname):
    fs = fullname.split('.')
    name_t = []
    start_flag = 0
    for item in fs:
        if not start_flag and not item[0].isupper():
            continue
        elif item[0].isdigit() or ("WEB" in item) or ("Blu" in item) or ((item[0] == "S" or item[0] == "E") and item[1].isdigit()):
            break
        name_t.append(item)
        start_flag = 1
    name = '.'.join(name_t)
    return name

def dispatch_episodes(path, linkdir):
    fname = os.path.basename(path)
    link_episodes(path, getname_episodes(fname), linkdir)


def removeChinese(context):
    filtrate = re.compile(u'[\u4E00-\u9FA5]') # non-Chinese unicode range
    context = filtrate.sub(r'', context) # remove all non-Chinese characters
    return context

def link_film(vf, root, linkdir):
    vf_en = removeChinese(os.path.basename(vf))
    print(vf_en)
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
    if os.path.exists(f"{vf_dir}/{fname}"):
        logging.error(f"films: check: file already exists \"{vf_dir}/{fname}\"")
        return
    logging.info(f"films: cmd: {link_cmd}")
    try:
        subprocess.check_output(link_cmd, stderr=subprocess.STDOUT, shell=True)
    except subprocess.CalledProcessError as e:
        logging.error(f"films: link: {e.output}")

def dispatch_films(path, linkdir):
    if not os.path.isdir(path) and is_video_or_subtitle(path):
        link_film(path, "", linkdir)
    for root, dirs, files in os.walk(path):
        vfiles = [f for f in files if is_video_or_subtitle(f)]
        if not vfiles:
            continue
        for vf in vfiles:
            link_film(vf, root, linkdir)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='qbittorrent download file dispatcher for nas')
    parser.add_argument('-f', "--file", required=True,
                        help="content path (root path for multifile torrent")
    parser.add_argument('-c', "--category", required=True,
                        help="torrent category")
    parser.add_argument("--config", default="config.ini",
                        help="config file")
    parser.add_argument('-n', "--name",
                        help="torrent name")
    # read config
    config = configparser.ConfigParser()
    config.read(args.config)
    logging.basicConfig(filename=config['default']['logpath'],
                        format='%(asctime)-15s %(levelname)s %(message)s',
                        level=logging.INFO)
    args = parser.parse_args()
    # path replacement
    for substr in config['docker-path-replacement']:
        if substr in args.file:
            ifile = args.file.replace(substr, config['docker-path-replacement'][substr])
            break

    for cate in config['film-link-binding']:
        if args.category == cate:
            dispatch_films(ifile, config['film-link-binding'][cate])
            sys.exit()

    for cate in config['episode-link-binding']:
        if args.category == cate:
            dispatch_episodes(ifile, config['episode-link-binding'][cate])
            sys.exit()