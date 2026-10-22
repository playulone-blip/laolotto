#!/usr/bin/env python3
"""
ดึงผลหวยลาว (หวยลาวพัฒนา) จาก kapook.com เก็บเป็น CSV และอัปเดตแบบต่อท้ายอัตโนมัติ

วิธีใช้
  pip install requests beautifulsoup4
  python laolotto_scraper.py            # ดึงเฉพาะงวดใหม่ (ถ้ายังไม่มีไฟล์ จะดึงย้อนหลังทั้งหมดให้)
  python laolotto_scraper.py --full     # บังคับดึงย้อนหลังทุกหน้าใหม่
  python laolotto_scraper.py --out my.csv
"""
import argparse
import csv
import re
import sys
import time
from datetime import date
from pathlib import Path

import requests
from bs4 import BeautifulSoup

BASE = "https://lottery.kapook.com/laolottery/history"
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; laolotto-csv/1.0)"}
FIELDS = ["date", "six", "last4", "last3", "last2"]
DATE_RE = re.compile(r"/laolottery/(\d{2})(\d{2})(\d{4})$")


def page_url(n: int) -> str:
    return BASE if n == 1 else f"{BASE}/{n}"


def parse_page(html: str):
    """คืน list ของ dict ผลหวยในหน้านั้น + จำนวนหน้าทั้งหมด (ถ้าหาเจอ)"""
    soup = BeautifulSoup(html, "html.parser")
    rows = []
    for h in soup.find_all(["h2", "h3"]):
        a = h.find("a", href=True)
        if not a:
            continue
        m = DATE_RE.search(a["href"])
        if not m:
            continue
        dd, mm, yy_be = int(m.group(1)), int(m.group(2)), int(m.group(3))
        table = h.find_next("table")
        if not table:
            continue
        cells = [td.get_text(strip=True) for td in table.find_all("td")]
        if len(cells) < 4 or not cells[0].isdigit():
            continue
        d = date(yy_be - 543, mm, dd)  # พ.ศ. -> ค.ศ.
        rows.append({
            "date": d.isoformat(),
            "six": cells[0].zfill(6),
            "last4": cells[1].zfill(4),
            "last3": cells[2].zfill(3),
            "last2": cells[3].zfill(2),
        })
    pages = [int(x) for x in re.findall(r"/laolottery/history/(\d+)", html)]
    return rows, (max(pages) if pages else 1)


def load_existing(path: Path):
    if not path.exists():
        return {}
    with path.open(newline="", encoding="utf-8") as f:
        return {r["date"]: r for r in csv.DictReader(f)}


def save(path: Path, data: dict):
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        for k in sorted(data):
            w.writerow(data[k])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="laolotto.csv")
    ap.add_argument("--full", action="store_true", help="ดึงทุกหน้าใหม่ทั้งหมด")
    ap.add_argument("--delay", type=float, default=1.0, help="หน่วงระหว่างหน้า (วินาที)")
    args = ap.parse_args()

    out = Path(args.out)
    data = {} if args.full else load_existing(out)
    incremental = bool(data)
    added = 0

    n, last_page = 1, 1
    while n <= last_page:
        r = requests.get(page_url(n), headers=HEADERS, timeout=30)
        r.raise_for_status()
        rows, last_page = parse_page(r.text)
        if not rows:
            break
        new_here = 0
        for row in rows:
            if row["date"] not in data:
                new_here += 1
                added += 1
            data[row["date"]] = row  # เขียนทับ เผื่อเว็บแก้เลข
        print(f"หน้า {n}/{last_page}: {len(rows)} งวด (ใหม่ {new_here})")
        # โหมดอัปเดต: ถ้าทั้งหน้าไม่มีงวดใหม่เลย แปลว่าตามทันแล้ว หยุดได้
        if incremental and new_here == 0:
            break
        n += 1
        time.sleep(args.delay)

    save(out, data)
    print(f"เสร็จ: เพิ่ม {added} งวด, รวม {len(data)} งวด -> {out}")


if __name__ == "__main__":
    sys.exit(main())
