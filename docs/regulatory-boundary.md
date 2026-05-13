# Regulatory Boundary Baseline (Step 135G-DOC)

## Current scope
- Internal AI HK equity paper-trading / decision-support system only.
- Human operator makes all real-money decisions outside the system.
- System does not provide client-facing advice.
- System does not execute trades.
- System does not connect to brokers.
- System does not manage client assets.

## Not currently provided
- client-facing investment advice
- public recommendation service
- solicitation
- discretionary account service
- robo-advice service
- broker-connected execution
- automated trading service
- real-money trading instruction

## Trigger for legal/regulatory review
Stop implementation and require explicit legal/regulatory review before any feature that:
- becomes client-facing or public
- provides personalized investment advice to external users
- presents AI output as recommendation/solicitation
- ranks or labels outputs as real buy/sell/hold advice
- connects to brokers
- creates real orders
- executes trades
- manages real-money portfolio or client assets
- allows autonomous execution
- changes the system from internal paper-only review to client-facing advisory/execution

## UI wording guardrail
- Keep `AI 模擬方向` and `只供模擬檢視`.
- Avoid `投資建議`, `買入建議`, `賣出建議`, `立即落盤`, `AI 最終決定`.
- Use `人手覆核`, `資料不足`, `暫時觀察`, `不是真實買賣建議`.

## Reference basis
- SFC suitability and online advisory/robo-advice guidance should be treated as review triggers if the system becomes client-facing/advisory/recommendation/solicitation/execution-capable.
- This document is not legal advice.
