# 📊 쇼핑몰 일일 리포트 자동화

> **매일 아침, 어제의 매출·재고 현황이 엑셀 리포트로 자동 도착합니다.**
> 수작업 데이터 정리 시간: 하루 2~3시간 → **0분**

## 어떤 문제를 해결하나요?

쇼핑몰을 운영하면 매일 반복되는 일이 있습니다.

- 채널별(스마트스토어·쿠팡·자사몰) 주문 데이터를 모아서 정리
- 어제 매출이 얼마였는지, 뭐가 잘 팔렸는지 확인
- 재고가 떨어진 상품이 없는지 체크 후 발주

이 프로젝트는 그 전 과정을 자동화합니다. 스케줄러에 등록해두면 **매일 아침 리포트가 자동 생성되고, 요약이 Slack으로 발송됩니다.**

## 리포트 구성 (4개 시트)

| 시트 | 내용 |
|------|------|
| 일일 요약 | 총매출·주문건수·객단가, **전일 대비 증감**, 채널별 매출 비중 |
| 상품별 매출 | 최근 7일 TOP 10 순위 + 막대 차트 |
| 재고 경고 | 안전재고 미달 상품, **발주 추천 수량**, 품절 임박 하이라이트 |
| 매출 추이 | 최근 14일 일별 매출 + 꺾은선 차트 |

## 빠른 시작

```bash
pip install pandas openpyxl

python generate_sample_data.py   # 데모용 샘플 데이터 생성
python report_generator.py       # 리포트 생성 → output/일일리포트_YYYY-MM-DD.xlsx
```

특정 날짜 기준 리포트:

```bash
python report_generator.py 2026-07-08
```

## 매일 자동 실행 설정

**Windows (작업 스케줄러):**

```
schtasks /create /tn "DailyShopReport" /tr "python C:\경로\report_generator.py" /sc daily /st 07:30
```

**Mac/Linux (cron):**

```
30 7 * * * cd /경로 && python report_generator.py
```

## Slack 알림 (선택)

환경변수만 설정하면 리포트 생성 후 요약이 Slack으로 발송됩니다.

```bash
export SLACK_WEBHOOK_URL="https://hooks.slack.com/services/..."
```

## 실전 적용 시

`generate_sample_data.py`(데모용)를 실제 데이터 소스로 교체하면 됩니다.

- 스마트스토어/쿠팡 **판매자 API 연동**
- 주문 내역 **엑셀 다운로드 폴더 감시**
- 자사몰 **DB 직접 조회**

카카오 알림톡, 이메일 등 다른 알림 채널로도 확장 가능합니다.

## 기술 스택

`Python` `pandas` `openpyxl` (차트 포함 엑셀 자동 생성) `Slack Webhook`

---

**개발: 최재훈** — 업무 자동화·AI 챗봇 구축 전문 | jh930306@gmail.com
이런 자동화가 필요하신가요? 어떤 반복 업무든 상담 환영합니다.
