# Operator Runbook (Beginner): Paper-Trading Risk Review

## 1) What this system does (plain language)

This system helps you review **AI stock ideas** in a **safe paper-trading mode**.

- **Paper trading** means fake trades for learning/testing.
- No real money is traded in this workflow.
- The system gives decision-support signals.
- A human (you) is still responsible for final decisions.

Think of this as a daily safety + quality check for AI-generated BUY ideas.

---

## 2) What is `run_id`?

A `run_id` is a unique number for one full system run (one batch/job execution).

- Every run gets its own `run_id`.
- The risk review CLI uses `run_id` to load results for that one run.
- If you choose the wrong `run_id`, you will review the wrong run.

In simple terms: **`run_id` is the receipt number for one day’s run.**

---

## 3) Daily operator workflow (step by step)

Use this checklist once per run/day.

1. **Get the target run ID**
   - Find the run you want to review from your normal operations view/logs.
   - Copy the exact numeric `run_id`.

2. **Run the risk review command**
   - In the project folder, run:

   ```bash
   python -m src.paper_risk_review_cli --run-id <id>
   ```

   Replace `<id>` with the real run id, for example:

   ```bash
   python -m src.paper_risk_review_cli --run-id 12345
   ```

3. **Read the JSON output**
   - Focus first on the top totals:
     - `total_blocked_buys`
     - `total_warning_buys`
     - `total_executed_buys`
   - Then review details in `per_ticker`.

4. **Record your review notes**
   - If blocked/warning counts are unusual, note it for follow-up.
   - If needed, escalate to the technical owner with the `run_id`.

---

## 4) How to read the output fields

The CLI prints JSON (structured text). You do not need to understand all fields—start with these:

### `total_blocked_buys`
How many BUY attempts were blocked by risk checks.

- Higher number = more BUYs stopped by guardrails.
- Not always bad; blocks can be protective.

### `total_warning_buys`
How many BUYs were allowed but had warning-level risk.

- Warning means “allowed with caution.”
- Review for patterns if this is high.

### `total_executed_buys`
How many BUYs were actually executed in paper trading.

- This is the count of completed paper BUY actions.

### `per_ticker`
Detailed review rows grouped by stock ticker.

- Use this to see **which stock** had blocked/warning/executed events.
- Each row gives compact context (event type, severity, message, and rule summary).

---

## 5) Quick interpretation guide

- **Many blocked, few executed**: the guardrails were strict for this run.
- **Many warnings**: allowed trades had elevated risk; review trend over time.
- **Healthy mix with clear reasons**: normal behavior for decision-support workflow.

Do not treat one run as final truth—look for trends across multiple runs.

---

## 6) Troubleshooting (short)

### Problem: “No output” or command fails immediately
- Check you are in the project directory.
- Check Python environment/dependencies are set up.
- Re-run the same command and copy the full error text for support.

### Problem: “Run not found” / empty review for a run id
- Confirm the `run_id` is correct.
- Confirm that run actually completed and persisted data.
- Try another known-good recent `run_id` to verify CLI works.

### Problem: JSON is hard to read
- Paste the output into any JSON formatter/viewer.
- Start with top totals first, then `per_ticker` details.

### Problem: Numbers look surprising
- Re-check you used the correct `run_id`.
- Compare with previous runs before escalating.
- Share the `run_id` and raw CLI output when asking for help.

---

## 7) Safety reminder

This workflow is for **paper-trading review** and **decision support**.
It does **not** authorize autonomous live trading.
