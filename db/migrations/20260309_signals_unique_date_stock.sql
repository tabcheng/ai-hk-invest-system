-- Milestone 1: prevent duplicate daily signals per stock.
-- Run once in Supabase SQL editor or migration pipeline.
ALTER TABLE public.signals
ADD CONSTRAINT signals_date_stock_unique UNIQUE (date, stock);
