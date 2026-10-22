#!/usr/bin/env python3
"""
ฝังข้อมูลจาก laolotto.csv ลงในบล็อก `var SEED = {...};` ของไฟล์ HTML

วิธีใช้ (วางไฟล์ทั้งหมดไว้โฟลเดอร์เดียวกัน)
  python update_html.py                 # ฝัง CSV -> สมุดผลหวยลาว.html
  python update_html.py --scrape        # รัน laolotto_scraper.py ก่อน แล้วค่อยฝัง
  python update_html.py --csv a.csv --html b.html
"""
import argparse
import csv
import re
import subprocess
import sys
from pathlib import Path


def parse_date(s: str) -> str:
    """รับ 2026-10-21 หรือ 10/21/2026 (รูปแบบที่ Excel บันทึก) -> 2026-10-21"""
    s = s.strip()
    m = re.fullmatch(r"(\d{4})-(\d{1,2})-(\d{1,2})", s)
    if m:
        y, mo, d = map(int, m.groups())
    else:
        m = re.fullmatch(r"(\d{1,2})/(\d{1,2})/(\d{4})", s)
        if not m:
            raise ValueError(f"อ่านวันที่ไม่ได้: {s!r}")
        a, b, y = map(int, m.groups())
        mo, d = (b, a) if a > 12 else (a, b)  # ปกติ M/D/Y; ถ้าตัวแรก >12 แปลว่า D/M/Y
    if y > 2400:
        y -= 543
    return f"{y}-{mo:02d}-{d:02d}"


def read_csv(path: Path) -> dict:
    seed, warn = {}, 0
    with path.open(newline="", encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            six = r["six"].strip().zfill(6)  # Excel มักตัดเลข 0 นำหน้า
            if not six.isdigit() or len(six) != 6:
                print(f"ข้ามแถวที่เลขผิดปกติ: {r}")
                continue
            if r.get("last2") and six[-2:] != r["last2"].strip().zfill(2):
                warn += 1
                print(f"เตือน: เลขท้าย 2 ตัวไม่ตรงกับเลข 6 ตัว ({r['date']}, {six})")
            seed[parse_date(r["date"])] = six
    if warn:
        print(f"พบแถวที่ไม่สอดคล้อง {warn} แถว (ใช้เลข 6 ตัวเป็นหลัก)")
    return seed


def seed_block(seed: dict) -> str:
    items = [f"'{k}':'{v}'" for k, v in sorted(seed.items())]
    lines = [", ".join(items[i:i + 6]) for i in range(0, len(items), 6)]
    return "var SEED = {\n  " + ",\n  ".join(lines) + "\n};"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", default="laolotto.csv")
    ap.add_argument("--html", default="สมุดผลหวยลาว.html")
    ap.add_argument("--scrape", action="store_true", help="รัน laolotto_scraper.py ก่อน")
    args = ap.parse_args()

    csv_path, html_path = Path(args.csv), Path(args.html)
    if args.scrape:
        here = Path(__file__).resolve().parent
        subprocess.run([sys.executable, str(here / "laolotto_scraper.py"), "--out", str(csv_path)], check=True)

    seed = read_csv(csv_path)
    if not seed:
        sys.exit("ไม่พบข้อมูลใน CSV ไม่แก้ไขไฟล์ HTML")

    html = html_path.read_text(encoding="utf-8")
    pat = re.compile(r"var SEED = \{.*?\n\};", re.S)
    if not pat.search(html):
        sys.exit("ไม่พบบล็อก 'var SEED = {...};' ในไฟล์ HTML")
    new_html = pat.sub(lambda _: seed_block(seed), html, count=1)

    if new_html == html:
        print("ข้อมูลเป็นปัจจุบันอยู่แล้ว ไม่มีการเปลี่ยนแปลง")
        return
    html_path.write_text(new_html, encoding="utf-8")
    ds = sorted(seed)
    print(f"ฝังข้อมูล {len(seed)} งวด ({ds[0]} ถึง {ds[-1]}) -> {html_path}")


if __name__ == "__main__":
    main()
