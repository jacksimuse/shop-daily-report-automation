# -*- coding: utf-8 -*-
"""Level 2 — 다중 채널 통합 자동화 파이프라인.

수집 → 정규화 → 검증 → 병합 → 리포트 생성 → 완료 요약
Level 1과의 차이:
  · 형식이 서로 다른 여러 데이터 소스를 설정 파일(config.json)만으로 통합
  · 데이터 검증: 중복 주문 제거, 금액 불일치 보정, 결측 행 격리
  · 단계별 로깅(pipeline.log) + 실패 시 자동 재시도
  · 새 채널 추가 = 코드 수정 없이 config에 매핑만 추가

실행:  python make_source_data.py && python pipeline.py
"""
import csv
import functools
import json
import logging
import subprocess
import sys
import time
from pathlib import Path

BASE = Path(__file__).parent
ROOT = BASE.parent

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(BASE / "pipeline.log", encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
log = logging.getLogger("pipeline")
CONFIG = json.loads((BASE / "config.json").read_text(encoding="utf-8"))


def retry(func):
    """일시적 오류(파일 잠김, 네트워크 등)에 대한 자동 재시도."""
    conf = CONFIG["retry"]

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        for attempt in range(1, conf["attempts"] + 1):
            try:
                return func(*args, **kwargs)
            except Exception as e:  # noqa: BLE001
                log.warning("%s 실패 (%d/%d회): %s", func.__name__, attempt, conf["attempts"], e)
                if attempt == conf["attempts"]:
                    raise
                time.sleep(conf["delay_seconds"])
    return wrapper


@retry
def collect(source: dict) -> list[dict]:
    """채널별 파일을 읽어 표준 스키마로 정규화."""
    path = BASE / source["file"]
    mapping = source["mapping"]  # 표준컬럼명 → 원본컬럼명
    rows = []
    with open(path, encoding="utf-8-sig") as f:
        for raw in csv.DictReader(f):
            rows.append({std: raw.get(org, "").strip() for std, org in mapping.items()}
                        | {"판매채널": source["name"]})
    log.info("수집: %s %d건 (%s)", source["name"], len(rows), path.name)
    return rows


def validate(rows: list[dict]) -> tuple[list[dict], list[str]]:
    """중복 제거·금액 검증·결측 격리. 문제 내역을 함께 반환한다."""
    issues, clean, seen = [], [], set()
    for r in rows:
        oid = r["주문번호"]
        if not all([oid, r["주문일자"], r["상품명"], r["수량"], r["단가"]]):
            issues.append(f"결측 제외: {oid or '(주문번호 없음)'} ({r['판매채널']})")
            continue
        if oid in seen:
            issues.append(f"중복 제거: {oid} ({r['판매채널']})")
            continue
        seen.add(oid)
        qty, price, total = int(r["수량"]), int(r["단가"]), int(r["금액"] or 0)
        if qty * price != total:
            issues.append(f"금액 보정: {oid} {total:,} → {qty * price:,}")
            total = qty * price
        clean.append({**r, "수량": qty, "단가": price, "금액": total})
    return clean, issues


def merge_and_save(rows: list[dict]) -> Path:
    """표준 형식으로 병합 저장 — Level 1 리포트 엔진이 그대로 읽는다."""
    out = ROOT / "data" / "orders.csv"
    out.parent.mkdir(exist_ok=True)
    with open(out, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["주문번호", "주문일자", "상품명", "수량", "단가", "금액", "판매채널"])
        for r in sorted(rows, key=lambda x: x["주문일자"]):
            w.writerow([r["주문번호"], r["주문일자"], r["상품명"], r["수량"], r["단가"], r["금액"], r["판매채널"]])
    return out


@retry
def run_report():
    result = subprocess.run(
        [sys.executable, str(ROOT / "report_generator.py")],
        capture_output=True, text=True, cwd=ROOT,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip()[-300:])
    log.info("리포트 생성: %s", result.stdout.strip())


def main():
    log.info("========== 파이프라인 시작 ==========")
    all_rows = []
    for source in CONFIG["sources"]:
        all_rows.extend(collect(source))

    clean, issues = validate(all_rows)
    for issue in issues:
        log.warning("데이터 검증 — %s", issue)
    log.info("검증 완료: 정상 %d건 / 문제 %d건 처리", len(clean), len(issues))

    out = merge_and_save(clean)
    log.info("병합 저장: %s", out)

    if CONFIG["report"]["run_after_merge"]:
        run_report()

    log.info("========== 파이프라인 완료 ==========")
    print(f"\n✅ 요약: {len(CONFIG['sources'])}개 채널 {len(all_rows)}건 수집 → "
          f"정제 {len(clean)}건 → 리포트 생성 완료 (문제 {len(issues)}건은 pipeline.log 참고)")


if __name__ == "__main__":
    main()
