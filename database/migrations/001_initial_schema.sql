CREATE EXTENSION IF NOT EXISTS pgcrypto;
CREATE EXTENSION IF NOT EXISTS pg_trgm;

CREATE TYPE asset_type AS ENUM ('stock','option','crypto','forex','commodity','index','bond','etf','mutual_fund','other');
CREATE TYPE api_key_provider AS ENUM ('twelvedata','alphavantage','massive','binance');

CREATE TABLE users (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    email text NOT NULL UNIQUE,
    password_hash text NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE profiles (
    id uuid PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    email text UNIQUE,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE refresh_sessions (
    token_hash text PRIMARY KEY,
    user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    expires_at timestamptz NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX refresh_sessions_user_id_idx ON refresh_sessions(user_id);
CREATE INDEX refresh_sessions_expires_at_idx ON refresh_sessions(expires_at);

CREATE FUNCTION set_updated_at() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN NEW.updated_at = now(); RETURN NEW; END $$;

CREATE FUNCTION create_user_profile() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN INSERT INTO profiles (id, email) VALUES (NEW.id, NEW.email); RETURN NEW; END $$;
CREATE TRIGGER users_create_profile AFTER INSERT ON users FOR EACH ROW EXECUTE FUNCTION create_user_profile();

CREATE TABLE api_keys (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    provider api_key_provider NOT NULL,
    encrypted_key bytea NOT NULL,
    key_prefix text NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (user_id, provider)
);
CREATE TABLE api_key_audit_log (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    provider api_key_provider NOT NULL,
    action text NOT NULL CHECK (action IN ('insert','update','delete','retrieve')),
    created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX api_key_audit_log_user_created_idx ON api_key_audit_log(user_id, created_at DESC);
CREATE FUNCTION audit_api_key() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  INSERT INTO api_key_audit_log(user_id, provider, action)
  VALUES (COALESCE(NEW.user_id, OLD.user_id), COALESCE(NEW.provider, OLD.provider), lower(TG_OP));
  RETURN COALESCE(NEW, OLD);
END $$;
CREATE TRIGGER api_keys_audit AFTER INSERT OR UPDATE OR DELETE ON api_keys FOR EACH ROW EXECUTE FUNCTION audit_api_key();
CREATE TRIGGER api_keys_updated BEFORE UPDATE ON api_keys FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TABLE exchanges (id serial PRIMARY KEY, code text NOT NULL UNIQUE);
CREATE TABLE symbols (
    symbol text PRIMARY KEY,
    name text NOT NULL,
    asset_type asset_type,
    exchange_id integer REFERENCES exchanges(id),
    twelvedata boolean NOT NULL DEFAULT false,
    yfinance boolean NOT NULL DEFAULT false,
    binance boolean NOT NULL DEFAULT false,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX symbols_name_trgm ON symbols USING gin (name gin_trgm_ops);
CREATE INDEX symbols_symbol_prefix ON symbols (symbol text_pattern_ops);
CREATE INDEX symbols_exchange_id ON symbols(exchange_id);
CREATE TRIGGER symbols_updated BEFORE UPDATE ON symbols FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TABLE ticker_workspaces (
    user_id uuid PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    data jsonb NOT NULL DEFAULT '{}'::jsonb,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE TRIGGER ticker_workspaces_updated BEFORE UPDATE ON ticker_workspaces FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TABLE user_scripts (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(), user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name text NOT NULL, code text NOT NULL, created_at timestamptz NOT NULL DEFAULT now(), updated_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE(user_id, name)
);
CREATE INDEX user_scripts_user_updated_idx ON user_scripts(user_id, updated_at DESC);
CREATE TRIGGER user_scripts_updated BEFORE UPDATE ON user_scripts FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TABLE user_strategies (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(), user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name text NOT NULL, code text NOT NULL, created_at timestamptz NOT NULL DEFAULT now(), updated_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE(user_id, name)
);
CREATE INDEX user_strategies_user_updated_idx ON user_strategies(user_id, updated_at DESC);
CREATE TRIGGER user_strategies_updated BEFORE UPDATE ON user_strategies FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TABLE symbol_comparisons (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(), user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    main_symbol text NOT NULL, comparison_symbol text NOT NULL, provider text NOT NULL, color text NOT NULL,
    series_type text NOT NULL CHECK (series_type IN ('line','candlestick')), position int NOT NULL DEFAULT 0,
    created_at timestamptz NOT NULL DEFAULT now(), UNIQUE(user_id, main_symbol, comparison_symbol)
);
CREATE INDEX symbol_comparisons_user_main_idx ON symbol_comparisons(user_id, main_symbol);
