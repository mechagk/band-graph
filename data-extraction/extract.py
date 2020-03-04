import itertools
import os
import re
from typing import List

import requests
from bs4 import BeautifulSoup, Tag
from dataclasses import dataclass
import hashlib
from multiprocessing.dummy import Pool as ThreadPool
import string


@dataclass
class BandMember:
    name: str
    url: str


@dataclass
class Band:
    page_name: str
    name: str
    url: str
    members: List[BandMember]
    has_subcategories: bool = False


@dataclass
class PageResult:
    bands: List[Band]
    next_url: str


def get_page(url: str) -> str:
    full_url = f"https://en.wikipedia.org{url}"
    h = hashlib.sha256(bytearray(full_url, 'UTF-8')).hexdigest()

    path = f"pages/{h}"
    if os.path.exists(path):
        with open(path, 'r') as f:
            text = f.read()
    else:
        r = requests.get(full_url)
        text = r.text
        with open(path, 'w') as f:
            f.write(text)

    return text


def create_band(anchor: Tag) -> Band:
    page_name = anchor.text
    name = re.sub(r"( \([a-zA-Z0-9 \-]+\))? members$", "", page_name)
    url = anchor.get('href')
    has_subcategories = anchor.find_previous_sibling(class_="CategoryTreeBullet") is not None
    members = get_band_members(url)

    return Band(page_name=page_name, name=name, url=url, members=members, has_subcategories=has_subcategories)


pool = ThreadPool(6)


def get_from_index(url: str) -> List[PageResult]:
    print(f"Getting bands from {url} ...")
    text = get_page(url)
    soup = BeautifulSoup(text, 'html.parser')
    list_items = soup.select(".mw-category-group .CategoryTreeItem > a")
    next_url = soup.find('a', title="Category:Musicians by band").get('href')
    result = PageResult(bands=list(pool.map(create_band, list_items)), next_url=next_url)
    if next_url is not None:
        return [result] + get_from_index(next_url)
    else:
        return [result]


def get_first() -> List[PageResult]:
    return get_from_index("/wiki/Category:Musicians_by_band")


def get_band_member(url: str) -> BandMember:
    text = get_page(url)
    soup = BeautifulSoup(text, 'html.parser')
    name = soup.select(".mw-parser-output p b")[0].text
    return BandMember(name=name, url=url)


def get_band_members(url: str) -> List[BandMember]:
    # print(f"Getting members from {url} ...")
    text = get_page(url)
    soup = BeautifulSoup(text, 'html.parser')

    all_subcategories = soup.select("#mw-pages .mw-category-group")

    if len(all_subcategories) > 0:
        list_items = itertools.chain(*[c.select('a') for c in all_subcategories if string.ascii_letters.find(c.find_next('h3').text) > -1])
    else:
        list_items = soup.select("#mw-pages .mw-content-ltr a")

    return [get_band_member(anchor.get('href')) for anchor in list_items]


if __name__ == "__main__":
    bands = itertools.chain(*[page.bands for page in get_first()])
    for band in bands:
        print(band.name)
        for member in band.members:
            print(f"{member.name}, ", end='')
        print()
