# -*- coding: utf-8 -*-
"""리포트 요약 알림 모듈 — Slack Incoming Webhook 사용.

환경변수 SLACK_WEBHOOK_URL 이 설정된 경우에만 발송한다.
(카카오 알림톡·이메일 등 다른 채널로 교체 가능한 구조)
"""
import json
import os
import urllib.request


def send_slack_summary(target, revenue, order_count, delta_pct, n_stock_alerts):
    url = os.environ.get("SLACK_WEBHOOK_URL")
    if not url:
        print("(알림 생략 — SLACK_WEBHOOK_URL 미설정)")
        return False

    text = (
        f"📊 *{target.isoformat()} 일일 리포트*\n"
        f"• 매출: {revenue:,}원 ({delta_pct:+.1f}% 전일 대비)\n"
        f"• 주문: {order_count}건\n"
        f"• 재고 경고: {n_stock_alerts}개 상품\n"
        f"상세 내용은 엑셀 리포트를 확인하세요."
    )
    req = urllib.request.Request(
        url,
        data=json.dumps({"text": text}).encode(),
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as res:
            ok = res.status == 200
        print("Slack 알림 발송 완료" if ok else f"Slack 응답 오류: {res.status}")
        return ok
    except Exception as e:  # noqa: BLE001
        print(f"Slack 알림 실패: {e}")
        return False
