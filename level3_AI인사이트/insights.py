# -*- coding: utf-8 -*-
"""Level 3 — AI 인사이트 대시보드.

단순 집계를 넘어 '판단'을 자동화한다:
  · 매출 이상 감지 (최근 7일 평균 대비 급등/급락)
  · 재고 소진 예측 (판매 속도 기반 D-day 계산 → 발주 시점 알림)
  · 상품 추세 분석 (뜨는 상품 / 지는 상품)
  · AI 경영 코멘트 (ANTHROPIC_API_KEY 설정 시 Claude가 데이터를 읽고 조언,
    미설정 시 규칙 기반 요약)
결과는 웹 대시보드(dashboard.html)로 생성 — 브라우저에서 바로 확인.

실행:  python insights.py   (사전 조건: ../data/ 에 orders.csv, inventory.csv)
"""
import json
import os
from datetime import timedelta
from pathlib import Path

import pandas as pd

BASE = Path(__file__).parent
ROOT = BASE.parent


def analyze() -> dict:
    orders = pd.read_csv(ROOT / "data" / "orders.csv", parse_dates=["주문일자"])
    inventory = pd.read_csv(ROOT / "data" / "inventory.csv")
    last = orders["주문일자"].max().date()

    day = orders[orders["주문일자"].dt.date == last]
    week = orders[orders["주문일자"].dt.date > last - timedelta(days=7)]
    prev_week = orders[(orders["주문일자"].dt.date > last - timedelta(days=14))
                       & (orders["주문일자"].dt.date <= last - timedelta(days=7))]

    day_rev = int(day["금액"].sum())
    week_avg = float(week.groupby(week["주문일자"].dt.date)["금액"].sum().mean())
    deviation = (day_rev - week_avg) / week_avg * 100 if week_avg else 0

    # 상품 추세: 최근 7일 vs 직전 7일
    cur = week.groupby("상품명")["금액"].sum()
    prev = prev_week.groupby("상품명")["금액"].sum()
    trend = ((cur - prev.reindex(cur.index).fillna(0)) / prev.reindex(cur.index).replace(0, pd.NA).fillna(1) * 100)
    rising = trend.sort_values(ascending=False).head(3)
    falling = trend.sort_values().head(3)

    # 재고 소진 예측: 최근 7일 일평균 판매량 기준 D-day
    daily_sales = (week.groupby("상품명")["수량"].sum() / 7).rename("일평균판매")
    inv = inventory.set_index("상품명").join(daily_sales).fillna({"일평균판매": 0})
    inv["소진예상일"] = inv.apply(
        lambda r: round(r["현재고"] / r["일평균판매"], 1) if r["일평균판매"] > 0 else float("inf"), axis=1)
    urgent = inv[inv["소진예상일"] <= 10].sort_values("소진예상일")

    daily = orders.groupby(orders["주문일자"].dt.date)["금액"].sum().tail(14)
    top10 = week.groupby("상품명")["금액"].sum().sort_values(ascending=False).head(10)
    channels = week.groupby("판매채널")["금액"].sum().sort_values(ascending=False)

    return {
        "date": last.isoformat(),
        "day_rev": day_rev, "week_avg": round(week_avg), "deviation": round(deviation, 1),
        "day_orders": len(day),
        "rising": [(k, round(v, 1)) for k, v in rising.items()],
        "falling": [(k, round(v, 1)) for k, v in falling.items()],
        "urgent_stock": [(idx, int(r["현재고"]), r["소진예상일"]) for idx, r in urgent.iterrows()],
        "daily": {d.isoformat(): int(v) for d, v in daily.items()},
        "top10": {k: int(v) for k, v in top10.items()},
        "channels": {k: int(v) for k, v in channels.items()},
    }


def make_comments(a: dict) -> list[str]:
    """규칙 기반 인사이트. API 키가 있으면 Claude 코멘트로 대체."""
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if api_key:
        try:
            return _claude_comments(a, api_key)
        except Exception:  # noqa: BLE001 — API 실패 시 규칙 기반으로 계속
            pass

    comments = []
    if a["deviation"] <= -30:
        comments.append(f"🔴 매출 급락 경보: 어제 매출이 주간 평균 대비 {abs(a['deviation'])}% 낮습니다. 광고·노출 상태 점검이 필요합니다.")
    elif a["deviation"] >= 30:
        comments.append(f"🟢 매출 급등: 주간 평균 대비 +{a['deviation']}%. 원인(이벤트·노출 증가)을 파악해 재현하세요.")
    else:
        comments.append(f"⚪ 어제 매출은 주간 평균 대비 {a['deviation']:+}% 로 정상 범위입니다.")
    if a["rising"]:
        name, pct = a["rising"][0]
        comments.append(f"📈 '{name}' 매출이 전주 대비 크게 상승했습니다. 재고 확보와 광고 집중을 검토하세요.")
    if a["falling"] and a["falling"][0][1] < -20:
        name, pct = a["falling"][0]
        comments.append(f"📉 '{name}' 매출이 전주 대비 {abs(pct)}% 하락했습니다. 가격·리뷰·경쟁 상품을 점검하세요.")
    if a["urgent_stock"]:
        top = a["urgent_stock"][0]
        comments.append(f"📦 재고 경보 {len(a['urgent_stock'])}건: '{top[0]}'은(는) 약 {top[2]}일 후 소진 예상입니다. 리드타임을 감안해 지금 발주하세요.")
    return comments


def _claude_comments(a: dict, api_key: str) -> list[str]:
    import anthropic
    client = anthropic.Anthropic(api_key=api_key)
    msg = client.messages.create(
        model=os.environ.get("CLAUDE_MODEL", "claude-haiku-4-5-20251001"),
        max_tokens=500,
        system="당신은 이커머스 데이터 분석가다. 데이터를 근거로 실행 가능한 조언을 한국어로 3~4개, 각 1~2문장으로 제시하라. JSON 배열로만 답하라.",
        messages=[{"role": "user", "content": json.dumps(a, ensure_ascii=False)}],
    )
    return json.loads(msg.content[0].text)


def render_dashboard(a: dict, comments: list[str]) -> Path:
    kpi_color = "#c0392b" if a["deviation"] <= -30 else ("#27ae60" if a["deviation"] >= 30 else "#1f4e79")
    stock_rows = "".join(
        f"<tr><td>{n}</td><td>{s}개</td><td class='{'danger' if d <= 5 else 'warn'}'>D-{d}</td></tr>"
        for n, s, d in a["urgent_stock"]) or "<tr><td colspan='3'>임박한 재고 없음 ✅</td></tr>"
    comment_items = "".join(f"<li>{c}</li>" for c in comments)

    html = f"""<!DOCTYPE html>
<html lang="ko"><head><meta charset="UTF-8"><title>AI 매출 대시보드 — {a['date']}</title>
<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.min.js"></script>
<style>
 body{{font-family:'Malgun Gothic',sans-serif;background:#f0f2f5;margin:0;padding:24px}}
 h1{{color:#1f4e79;font-size:22px}} .grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:16px}}
 .card{{background:#fff;border-radius:12px;padding:20px;box-shadow:0 1px 4px rgba(0,0,0,.08)}}
 .kpi{{font-size:30px;font-weight:bold;color:{kpi_color}}} .kpi-label{{font-size:13px;color:#888}}
 .insights li{{margin-bottom:10px;line-height:1.6;font-size:14px}}
 table{{width:100%;border-collapse:collapse;font-size:13px}} td,th{{padding:8px;border-bottom:1px solid #eee;text-align:left}}
 .danger{{color:#c0392b;font-weight:bold}} .warn{{color:#e67e22;font-weight:bold}}
</style></head><body>
<h1>🧠 AI 매출 인사이트 대시보드 <small style="color:#888;font-size:14px">{a['date']} 기준 · 자동 생성</small></h1>
<div class="grid">
 <div class="card"><div class="kpi-label">어제 매출 (주간 평균 대비)</div>
  <div class="kpi">{a['day_rev']:,}원</div><div style="color:{kpi_color};font-weight:bold">{a['deviation']:+}%</div></div>
 <div class="card"><div class="kpi-label">어제 주문</div><div class="kpi">{a['day_orders']}건</div>
  <div class="kpi-label">주간 일평균 매출 {a['week_avg']:,}원</div></div>
 <div class="card"><div class="kpi-label">AI 인사이트</div><ul class="insights">{comment_items}</ul></div>
</div>
<div class="grid" style="margin-top:16px">
 <div class="card"><canvas id="daily"></canvas></div>
 <div class="card"><canvas id="top10"></canvas></div>
 <div class="card"><h3 style="margin-top:0;font-size:15px">📦 재고 소진 예측 (10일 이내)</h3>
  <table><tr><th>상품</th><th>현재고</th><th>소진 예상</th></tr>{stock_rows}</table></div>
</div>
<script>
new Chart(document.getElementById('daily'), {{type:'line',
 data:{{labels:{json.dumps(list(a['daily'].keys()))},
  datasets:[{{label:'일별 매출',data:{json.dumps(list(a['daily'].values()))},borderColor:'#2e75b6',tension:.3,fill:false}}]}},
 options:{{plugins:{{title:{{display:true,text:'최근 14일 매출 추이'}}}}}}}});
new Chart(document.getElementById('top10'), {{type:'bar',
 data:{{labels:{json.dumps(list(a['top10'].keys()), ensure_ascii=False)},
  datasets:[{{label:'최근 7일 매출',data:{json.dumps(list(a['top10'].values()))},backgroundColor:'#2e75b6'}}]}},
 options:{{indexAxis:'y',plugins:{{title:{{display:true,text:'상품별 매출 TOP 10 (7일)'}}}}}}}});
</script></body></html>"""
    out = BASE / "dashboard.html"
    out.write_text(html, encoding="utf-8")
    return out


def main():
    a = analyze()
    comments = make_comments(a)
    out = render_dashboard(a, comments)
    print(f"대시보드 생성 완료 → {out}")
    print("\n[AI 인사이트]")
    for c in comments:
        print(" ", c)


if __name__ == "__main__":
    main()
