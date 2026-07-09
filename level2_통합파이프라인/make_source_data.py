# -*- coding: utf-8 -*-
"""Level 2 데모용 — 채널별로 '형식이 서로 다른' 원본 데이터를 생성한다.

실무에서 흔한 상황을 재현: 스마트스토어·쿠팡·자사몰이 각각
컬럼명도 형식도 다른 파일을 준다. 일부러 더러운 데이터(중복 주문,
금액 불일치, 결측)도 섞어서 파이프라인의 검증 기능을 보여준다.
"""
import csv
import random
import sys
from pathlib import Path

BASE = Path(__file__).parent
sys.path.insert(0, str(BASE.parent))
from generate_sample_data import PRODUCTS, generate_orders  # noqa: E402

random.seed(7)
SOURCE_DIR = BASE / "data_sources"


def main():
    SOURCE_DIR.mkdir(exist_ok=True)
    rows = generate_orders()  # 표준: [주문번호, 일자, 상품명, 수량, 단가, 금액, 채널]
    by_channel = {"스마트스토어": [], "쿠팡": [], "자사몰": []}
    for r in rows:
        by_channel[r[6]].append(r)

    # 더러운 데이터 주입 — 파이프라인 검증 단계가 걸러내는 것을 시연
    dup = by_channel["스마트스토어"][3]
    by_channel["스마트스토어"].append(dup)                      # 중복 주문
    bad = list(by_channel["쿠팡"][5]); bad[5] = bad[5] + 1000   # 금액 불일치
    by_channel["쿠팡"][5] = bad
    miss = list(by_channel["자사몰"][2]); miss[3] = ""          # 수량 결측
    by_channel["자사몰"][2] = miss

    # 채널마다 다른 스키마로 저장
    with open(SOURCE_DIR / "smartstore_orders.csv", "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["주문ID", "일자", "상품", "개수", "판매단가", "결제금액"])
        w.writerows([r[0], r[1], r[2], r[3], r[4], r[5]] for r in by_channel["스마트스토어"])

    with open(SOURCE_DIR / "coupang_orders.csv", "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["order_no", "date", "item_name", "qty", "unit_price", "total"])
        w.writerows([r[0], r[1], r[2], r[3], r[4], r[5]] for r in by_channel["쿠팡"])

    with open(SOURCE_DIR / "mall_orders.csv", "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["번호", "주문일", "제품명", "수량", "가격", "합계"])
        w.writerows([r[0], r[1], r[2], r[3], r[4], r[5]] for r in by_channel["자사몰"])

    print(f"채널별 원본 데이터 생성 완료 → {SOURCE_DIR}")
    for name, rows_ in by_channel.items():
        print(f"  - {name}: {len(rows_)}건")


if __name__ == "__main__":
    main()
