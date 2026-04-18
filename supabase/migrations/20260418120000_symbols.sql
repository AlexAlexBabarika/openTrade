-- Canonical symbol directory shared across providers for autocomplete + badges.
-- Reuses asset_type enum from 20260311123025_asset_type.sql and set_updated_at()
-- from 20260312091500_profiles.sql.
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- Exchange lookup: hundreds of symbols share the same exchange code (NASDAQ,
-- NYSE, BINANCE, …), so we store the code once and reference it by id.
CREATE TABLE public.exchanges (
    id    serial PRIMARY KEY,
    code  text NOT NULL UNIQUE
);

CREATE TABLE public.symbols (
    symbol              text PRIMARY KEY,
    name                text NOT NULL,
    asset_type          asset_type,
    exchange_id         integer REFERENCES public.exchanges(id),
    twelvedata          boolean NOT NULL DEFAULT false,
    yfinance            boolean NOT NULL DEFAULT false,
    binance             boolean NOT NULL DEFAULT false,
    created_at          timestamptz NOT NULL DEFAULT now(),
    updated_at          timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX symbols_name_trgm ON public.symbols USING gin (name gin_trgm_ops);
CREATE INDEX symbols_symbol_prefix ON public.symbols (symbol text_pattern_ops);
CREATE INDEX symbols_exchange_id ON public.symbols (exchange_id);

DROP TRIGGER IF EXISTS symbols_set_updated_at ON public.symbols;
CREATE TRIGGER symbols_set_updated_at
    BEFORE UPDATE ON public.symbols
    FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

ALTER TABLE public.symbols    ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.exchanges  ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "symbols are publicly readable" ON public.symbols;
CREATE POLICY "symbols are publicly readable"
    ON public.symbols FOR SELECT
    TO authenticated, anon
    USING (true);

DROP POLICY IF EXISTS "exchanges are publicly readable" ON public.exchanges;
CREATE POLICY "exchanges are publicly readable"
    ON public.exchanges FOR SELECT
    TO authenticated, anon
    USING (true);
-- No insert/update/delete policies on either table: only service_role can write.
