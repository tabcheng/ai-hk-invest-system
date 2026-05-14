# Mini App Accessibility Checklist (Step 135G follow-up baseline)

Use this checklist for Mini App UI changes (especially tabs / first-view / card restructuring):

1. Headings describe purpose clearly.
2. Labels are Traditional Chinese primary (English helper only when needed).
3. `tab` / `tabpanel` references match (`aria-labelledby` and panel ownership are correct).
4. Tab order is stable and predictable.
5. Controls and touch targets are mobile-friendly.
6. Hidden content is not focusable.
7. Technical details are collapsed with clear labels (for example `查看技術資料`).
8. Meaning is not color-only.
9. Safety wording is visible (`只供模擬檢視`, `不建立訂單`, `不連接券商`, `不是真實買賣建議`).
10. No raw enum/internal field is used as first-layer UX text.

## Step 135I Mini App accessibility checks
- Tab/tabpanel mapping must stay correct after any tab structure change (`role=tab` + `data-tab-panel` + `aria-labelledby`).
- Collapsed sections must use meaningful Chinese-first labels。
- Hidden collapsed content should not leave confusing focus order for keyboard navigation.
- Status meaning cannot rely on color only; wording must carry meaning.
- Operator-facing labels should be Chinese-first and descriptive.


## Step 135J accessibility checks
- `資料缺口行動`/`下一步資料行動` uses readable text bullets (not color-only signals).
- Data-gap interpretation caveats are visible as text (`解讀限制`), not icon/color only.
- `查看技術資料` remains collapsible and keyboard accessible.

## Step 135K accessibility checks
- `資料缺口行動` and `解讀限制` remain readable text (not color-only/icon-only meaning).
- Backend-structured data action text still renders as plain readable list items.
- `查看技術資料` collapsed details remain keyboard accessible and unchanged as secondary layer.

## Step 135L accessibility checks
- `去向` / `影響` are rendered as readable text in Stock Review action rows (not color-only).
- Today `你下一步要做咩` route hints remain plain text and summary-first.
- `查看技術資料` remains collapsed and keyboard accessible after routing text additions.
