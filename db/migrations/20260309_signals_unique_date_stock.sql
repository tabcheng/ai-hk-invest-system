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
        -- Keep one row per (date, stock) so the unique constraint can be applied safely.
        DELETE FROM public.signals s
        USING (
            SELECT ctid
            FROM (
                SELECT ctid,
                       ROW_NUMBER() OVER (PARTITION BY date, stock ORDER BY ctid) AS row_num
                FROM public.signals
            ) ranked
            WHERE ranked.row_num > 1
        ) duplicates
        WHERE s.ctid = duplicates.ctid;

        ALTER TABLE public.signals
        ADD CONSTRAINT signals_date_stock_unique UNIQUE (date, stock);
    END IF;
END
$$;
