-- schema.sql — создание структуры БД (согласовано с Backend)
-- Запуск: psql -U postgres -d pricetag -f schema.sql

CREATE EXTENSION IF NOT EXISTS "pgcrypto";  -- для gen_random_uuid()

CREATE TABLE IF NOT EXISTS recognitions (
    id              UUID            PRIMARY KEY DEFAULT gen_random_uuid(),
    image_data      BYTEA           NOT NULL,
    raw_text        TEXT,
    extracted_price NUMERIC(10, 2),
    confidence      NUMERIC(4, 3),
    is_valid        BOOLEAN         DEFAULT NULL,  -- NULL = не проверено
    correct_price   NUMERIC(10, 2),               -- заполняется оператором
    created_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

-- Индекс для быстрой фильтрации по статусу и дате
CREATE INDEX IF NOT EXISTS idx_recognitions_is_valid ON recognitions (is_valid);
CREATE INDEX IF NOT EXISTS idx_recognitions_created_at ON recognitions (created_at DESC);

COMMENT ON TABLE recognitions IS 'Результаты распознавания ценников';
COMMENT ON COLUMN recognitions.is_valid IS 'NULL — не проверено, TRUE — верно, FALSE — ошибка';
COMMENT ON COLUMN recognitions.image_data IS 'BLOB картинки. MVP: хранится в Postgres. В продакшне перенести в MinIO/S3';
