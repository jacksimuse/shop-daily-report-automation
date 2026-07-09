# -*- coding: utf-8 -*-
"""샘플 데이터 생성기 — 실제 쇼핑몰 대신 데모용 주문/재고 데이터를 만든다.

실전에서는 이 파일 대신 스마트스토어/쿠팡 API 또는 주문 엑셀 다운로드를
data/ 폴더에 넣는 수집 모듈로 교체하면 된다.
"""
import csv
import random
from datetime import date, timedelta
from pathlib import Path

random.seed(42)  # 데모 재현성

DATA_DIR = Path(__file__).parent / "data"

PRODUCTS = [
    # (상품명, 판매가, 인기도 가중치, 안전재고)
    ("프리미엄 텀블러 500ml", 18900, 10, 30),
    ("스테인리스 빨대 세트", 6900, 8, 50),
    ("휴대용 미니 가습기", 24900, 7, 20),
    ("무선 충전 패드 15W", 19900, 9, 25),
    ("데스크 모니터 받침대", 32900, 5, 15),
    ("메모리폼 손목 쿠션", 12900, 6, 40),
    ("LED 무드등", 15900, 7, 30),
    ("접이식 노트북 거치대", 27900, 8, 20),
    ("차량용 핸드폰 거치대", 13900, 6, 35),
    ("보온보냉 도시락 가방", 16900, 5, 25),
    ("멀티탭 정리함", 9900, 4, 45),
    ("스마트 체중계", 29900, 6, 15),
    ("블루투스 미니 스피커", 35900, 7, 18),
    ("USB 선풍기", 8900, 9, 60),
    ("여행용 파우치 세트", 14900, 5, 30),
]
CHANNELS = [("스마트스토어", 0.5), ("쿠팡", 0.35), ("자사몰", 0.15)]
DAYS = 30


def generate_orders():
    rows = []
    order_no = 1000
    today = date.today()
    for d in range(DAYS, 0, -1):
        day = today - timedelta(days=d - 1)
        weekend_boost = 1.4 if day.weekday() >= 5 else 1.0
        n_orders = max(3, int(random.gauss(18, 6) * weekend_boost))
        for _ in range(n_orders):
            prod = random.choices(PRODUCTS, weights=[p[2] for p in PRODUCTS])[0]
            channel = random.choices([c[0] for c in CHANNELS], weights=[c[1] for c in CHANNELS])[0]
            qty = random.choices([1, 2, 3], weights=[0.7, 0.2, 0.1])[0]
            order_no += 1
            rows.append([f"ORD{order_no}", day.isoformat(), prod[0], qty, prod[1], qty * prod[1], channel])
    return rows


def generate_inventory():
    rows = []
    for name, price, _, safety in PRODUCTS:
        stock = random.randint(0, safety * 3)
        rows.append([name, stock, safety, price])
    return rows


def main():
    DATA_DIR.mkdir(exist_ok=True)
    with open(DATA_DIR / "orders.csv", "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["주문번호", "주문일자", "상품명", "수량", "단가", "금액", "판매채널"])
        w.writerows(generate_orders())
    with open(DATA_DIR / "inventory.csv", "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["상품명", "현재고", "안전재고", "판매가"])
        w.writerows(generate_inventory())
    print(f"샘플 데이터 생성 완료 → {DATA_DIR}")


if __name__ == "__main__":
    main()
