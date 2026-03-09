-- Milestone 1: prevent duplicate daily signals per stock.
-- Run once in Supabase SQL editor or migration pipeline.
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'signals_date_stock_unique'
          AND conrelid = 'public.signals'::regclass
    ) THEN
        ALTER TABLE public.signals
        ADD CONSTRAINT signals_date_stock_unique UNIQUE (date, stock);
    END IF;
END
$$;
