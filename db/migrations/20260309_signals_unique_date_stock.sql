-- Milestone 1: prevent duplicate daily signals per stock.
-- Run once in Supabase SQL editor or migration pipeline.
DO $$
DECLARE
    dedup_order_expr text;
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'signals_date_stock_unique'
          AND conrelid = 'public.signals'::regclass
    ) THEN
        -- Prefer deterministic retention of the most recent row when deduplicating.
        IF EXISTS (
            SELECT 1
            FROM information_schema.columns
            WHERE table_schema = 'public'
              AND table_name = 'signals'
              AND column_name = 'created_at'
        ) THEN
            dedup_order_expr := 'created_at DESC NULLS LAST, ctid DESC';
        ELSIF EXISTS (
            SELECT 1
            FROM information_schema.columns
            WHERE table_schema = 'public'
              AND table_name = 'signals'
              AND column_name = 'id'
        ) THEN
            dedup_order_expr := 'id DESC, ctid DESC';
        ELSE
            dedup_order_expr := 'ctid DESC';
        END IF;

        EXECUTE format(
            $sql$
            WITH ranked AS (
                SELECT
                    ctid,
                    ROW_NUMBER() OVER (
                        PARTITION BY date, stock
                        ORDER BY %s
                    ) AS row_num
                FROM public.signals
            ),
            duplicates AS (
                SELECT ctid
                FROM ranked
                WHERE row_num > 1
            )
            DELETE FROM public.signals s
            USING duplicates d
            WHERE s.ctid = d.ctid;
            $sql$,
            dedup_order_expr
        );

        ALTER TABLE public.signals
        ADD CONSTRAINT signals_date_stock_unique UNIQUE (date, stock);
    END IF;
END
$$;
