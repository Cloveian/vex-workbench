# /// script
# requires-python = ">=3.10"
# dependencies = ["selenium"]
# ///
# usage: uv run tools/fetch_vex_cad.py [--limit N] [--list-only] [--headless] [--have DIR]
#   pages through vex's cad search (V5 product line) in firefox on a copy of my profile's cookies, downloads every "DOWNLOAD CAD" file thats not in --have yet into downloads/vex-v5/ + manifest.csv

import argparse
import configparser
import csv
import re
import shutil
import sys
import tempfile
import time
from pathlib import Path

from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.support.ui import WebDriverWait

START_URL = (
    "https://www.vexrobotics.com/catalogsearch/result/?q=__empty__&vex_site=cads"
    "&int_source=v5_landing_page&int_location=banner&int_link=shop_now_quote&int_position=1"
    "&vex_m2_vexrobotics_cads%5BrefinementList%5D%5Bproduct_lines%5D%5B0%5D=VEX%20V5"
)
ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "downloads" / "vex-v5"
MANIFEST = OUT_DIR / "manifest.csv"
HAVE_DIR = ROOT / "vex-step"
FIELDS = ["name", "sku", "product_url", "cad_url", "upload_id", "filename", "thumbnail_url", "bytes"]
MAX_PAGES = 200

FIREFOX = "/usr/bin/firefox"
PROFILES = Path.home() / ".config" / "mozilla" / "firefox"
SAVE_TYPES = ",".join(["application/octet-stream", "application/step", "application/stp", "model/step",
                       "application/zip", "application/x-zip-compressed", "binary/octet-stream"])

BLOCK_MARKERS = ["access temporarily blocked", "just a moment", "verify you are human",
                 "cf-challenge", "captcha", "attention required"]
WAIT_FOR_ME = True  # headed: wait for me to do a bot check by hand
SOLVE_WAIT = 180  # s

# page has 5 searches (products, cads, pages, resources, news) each with its own pagenation, so only cards with a cad link count
# one object per card, climbs up from the cad link until the parent would hold a 2nd one
SCRAPE_JS = """
() => [...document.querySelectorAll('a.cad-link')].map(cad => {
  let card = cad;
  while (card.parentElement && card.parentElement.querySelectorAll('a.cad-link').length === 1)
    card = card.parentElement;
  const a = card.querySelector('a.instant-search-name-link');
  const img = card.querySelector('.cad-image img');
  return {
    name: a ? (a.getAttribute('aria-label') || a.textContent || '').trim() : '',
    product_url: a ? a.href : '',
    thumbnail_url: img ? (img.currentSrc || img.src || img.dataset.src || '') : '',
    cad_url: cad.href,
  };
})
"""
# cads next link is the visable one that only pages the cads index, the others carry page= or their own [page] keys
NEXT_JS = """
const cadsOnly = a => {
  const keys = [...new URL(a.href).searchParams.keys()].filter(k => k === 'page' || k.endsWith('[page]'));
  return keys.length === 1 && keys[0] === 'vex_m2_vexrobotics_cads[page]';
};
const links = [...document.querySelectorAll('.ais-Pagination-item--nextPage:not(.ais-Pagination-item--disabled) a')];
return links.find(a => a.getClientRects().length && cadsOnly(a)) || null;
"""


def blocked(msg):
    # bot wall / 403, dont fight it, just stop
    print("BLOCKED, stopping. the site said:\n" + msg, file=sys.stderr)
    sys.exit(2)


def bot_page(driver):
    try:
        text = driver.find_element(By.TAG_NAME, "body").text
    except NoSuchElementException:
        text = ""
    hit = any(m in (driver.title + " " + text).lower() for m in BLOCK_MARKERS)
    return text if hit else None


def check_blocked(driver):
    text = bot_page(driver)
    if text is None:
        return
    if WAIT_FOR_ME and "access temporarily blocked" not in text.lower():
        print(f"bot check in the firefox window, do it there, waiting {SOLVE_WAIT} s", file=sys.stderr)
        end = time.time() + SOLVE_WAIT
        while time.time() < end:
            time.sleep(2)
            if bot_page(driver) is None:
                return
    blocked(f"url={driver.current_url}\n" + text[:1200])


def upload_id_of(url):
    m = re.search(r"/upload_id/([^/?#]+)", url)
    return m.group(1) if m else ""


def sku_of(url):
    m = re.search(r"/([^/]+?)\.html", url)
    return m.group(1) if m else ""


def default_profile():
    ini = configparser.ConfigParser()
    ini.read(PROFILES / "profiles.ini")
    # Install section is the one firefox opens, Default=1 is the old one
    for s in ini.sections():
        if s.startswith("Install") and ini[s].get("Default"):
            return PROFILES / ini[s]["Default"]
    for s in ini.sections():
        if ini[s].get("Default") == "1":
            return PROFILES / ini[s]["Path"]
    sys.exit(f"no default profile in {PROFILES / 'profiles.ini'}")


def cookie_profile():
    src = default_profile()
    dst = Path(tempfile.mkdtemp(prefix="vexcad-ff-"))
    # just the cookies, whole profile is 1.6 GB and locked while firefox is open
    for p in src.glob("cookies.sqlite*"):
        shutil.copy2(p, dst)
    print(f"cookies from {src.name}", file=sys.stderr)
    return dst


def open_firefox(profile, headless):
    opts = Options()
    opts.binary_location = FIREFOX
    opts.add_argument("-profile")
    opts.add_argument(str(profile))
    if headless:
        opts.add_argument("-headless")
    # straight into OUT_DIR, no save dialog
    opts.set_preference("browser.download.folderList", 2)
    opts.set_preference("browser.download.dir", str(OUT_DIR))
    opts.set_preference("browser.download.useDownloadDir", True)
    opts.set_preference("browser.download.always_ask_before_handling_new_types", False)
    opts.set_preference("browser.helperApps.neverAsk.saveToDisk", SAVE_TYPES)
    return webdriver.Firefox(options=opts)


def wait_for_hits(driver):
    # algolia renders client side, needs a real browser
    try:
        WebDriverWait(driver, 30).until(lambda d: d.find_elements(By.CSS_SELECTOR, "a.cad-link"))
    except TimeoutException:
        return []
    time.sleep(1.5)  # let the rest of the hits settle
    return driver.execute_script("return (" + SCRAPE_JS + ")()")


def collect(driver):
    # clicks the cad box's next button like i would, keeps the V5 filter
    driver.get(START_URL)
    check_blocked(driver)
    found = {}
    pages = 0
    for n in range(1, MAX_PAGES + 1):
        cards = wait_for_hits(driver)
        check_blocked(driver)
        new = 0
        for c in cards:
            if upload_id_of(c["cad_url"]) not in found:
                found[upload_id_of(c["cad_url"])] = c
                new += 1
        print(f"page {n}: {len(cards)} cards, {new} new", file=sys.stderr)
        pages = n
        nxt = driver.execute_script(NEXT_JS)
        if not nxt:
            print("no next button, that's the last page", file=sys.stderr)
            break
        if not new:
            print("page added nothing new, stopping", file=sys.stderr)
            break
        first = cards[0]["cad_url"]
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'})", nxt)
        nxt.click()
        # wait for the cad hits to actually change
        try:
            WebDriverWait(driver, 20).until(lambda d: d.execute_script(
                "const a = document.querySelector('a.cad-link'); return a && a.href !== arguments[0]", first))
        except TimeoutException:
            print(f"page {n + 1} never showed up, stopping there", file=sys.stderr)
            break
        time.sleep(1)
    rows = []
    for c in found.values():
        rows.append({
            "name": c["name"], "sku": sku_of(c["product_url"]), "product_url": c["product_url"],
            "cad_url": c["cad_url"], "upload_id": upload_id_of(c["cad_url"]),
            "filename": "", "thumbnail_url": c["thumbnail_url"], "bytes": "",
        })
    return pages, rows


def load_manifest():
    if not MANIFEST.exists():
        return {}
    with MANIFEST.open(newline="") as f:
        return {r["upload_id"]: r for r in csv.DictReader(f) if r.get("upload_id")}


def write_manifest(rows):
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    tmp = MANIFEST.with_suffix(".csv.tmp")
    with tmp.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)
    tmp.replace(MANIFEST)


def name_key(name):
    # vex saves '3/8" OD Spacer' as "3_8 OD Spacer (276-8019-001).step", some card names already end in (sku)
    name = re.sub(r"\s*\([\d-]+\)\s*$", "", name)
    return " ".join(name.replace("/", "_").replace('"', "").lower().split())


def have_index(folder):
    names, skus = set(), set()
    for p in folder.rglob("*"):
        if not p.is_file():
            continue
        m = re.search(r"\(([\d-]+)\)\s*$", p.stem)
        if m:
            skus.add(m.group(1))
        names.add(name_key(p.stem))
    return names, skus


def already_have(row, old):
    prev = old.get(row["upload_id"])
    if prev and prev.get("filename"):
        p = OUT_DIR / prev["filename"]
        if p.exists() and p.stat().st_size > 0:
            return prev["filename"], p.stat().st_size
    return None


def wait_download(driver, before, timeout=300):
    # firefox makes an empty final file + name.part, done once the .part is gone
    url0 = driver.current_url
    end = time.time() + timeout
    while time.time() < end:
        time.sleep(0.5)
        if driver.current_url != url0:
            # served a page
            check_blocked(driver)
            return None
        now = {p.name for p in OUT_DIR.iterdir()} - before
        if any(n.endswith(".part") for n in now):
            continue
        # the empty placeholder can show up before the .part does
        done = [n for n in now if not n.endswith(".tmp") and n != MANIFEST.name and (OUT_DIR / n).stat().st_size]
        if done:
            return done[0]
    return None


def download(driver, row):
    before = {p.name for p in OUT_DIR.iterdir()}
    # driver.get would sit waiting on a page load a download never finishes
    driver.execute_script("window.location.href = arguments[0]", row["cad_url"])
    name = wait_download(driver, before)
    if not name:
        print(f"  ! no file for {row['cad_url']}, skipping", file=sys.stderr)
        if driver.current_url != START_URL:
            driver.get(START_URL)
        return None
    return name, (OUT_DIR / name).stat().st_size


def main():
    global WAIT_FOR_ME
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=None, help="max files to download this run")
    ap.add_argument("--list-only", action="store_true", help="write the manifest + print what's missing, download nothing")
    ap.add_argument("--headless", action="store_true", help="no firefox window (bot checks just stop it)")
    ap.add_argument("--have", type=Path, default=HAVE_DIR, help="folder of files i already have")
    args = ap.parse_args()
    WAIT_FOR_ME = not args.headless

    profile = cookie_profile()
    driver = open_firefox(profile, args.headless)
    try:
        pages, rows = collect(driver)
        print(f"{pages} pages, {len(rows)} unique upload_ids", file=sys.stderr)

        old = load_manifest()
        for r in rows:
            have = already_have(r, old)
            if have:
                r["filename"], r["bytes"] = have
        write_manifest(rows)

        names, skus = have_index(args.have) if args.have.is_dir() else (set(), set())
        todo = []
        for r in rows:
            if r["filename"] or name_key(r["name"]) in names or r["sku"] in skus:
                continue
            todo.append(r)
        print(f"{len(rows) - len(todo)} already here or in {args.have.name}/, {len(todo)} missing", file=sys.stderr)

        if args.list_only:
            for r in todo:
                print(f"  missing: {r['sku']} {r['name']}", file=sys.stderr)
            print(f"manifest: {MANIFEST}", file=sys.stderr)
            return 0

        done = 0
        for i, r in enumerate(todo, 1):
            if args.limit is not None and done >= args.limit:
                break
            if done:
                time.sleep(1.5)  # be nice
            print(f"[{i}/{len(todo)}] {r['sku']} {r['name']}", file=sys.stderr)
            got = download(driver, r)
            done += 1
            if got:
                r["filename"], r["bytes"] = got
                print(f"  {got[0]} ({got[1]} bytes)", file=sys.stderr)
                write_manifest(rows)
        print(f"downloaded {done}, manifest: {MANIFEST}", file=sys.stderr)
        return 0
    finally:
        driver.quit()
        shutil.rmtree(profile, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
