-- migration_add_fields.sql — Добавление новых полей в таблицу recognitions
-- Запуск: psql -U postgres -d pricetag -f migration_add_fields.sql

-- Добавляем новые поля, если их еще нет
DO $$ 
BEGIN
    -- product_name
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name='recognitions' AND column_name='product_name') THEN
        ALTER TABLE recognitions ADD COLUMN product_name TEXT;
    END IF;
    
    -- barcode
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name='recognitions' AND column_name='barcode') THEN
        ALTER TABLE recognitions ADD COLUMN barcode TEXT;
    END IF;
    
    -- weight
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name='recognitions' AND column_name='weight') THEN
        ALTER TABLE recognitions ADD COLUMN weight TEXT;
    END IF;
    
    -- store
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name='recognitions' AND column_name='store') THEN
        ALTER TABLE recognitions ADD COLUMN store TEXT;
    END IF;
END $$;

-- Добавляем комментарии к полям
COMMENT ON COLUMN recognitions.product_name IS 'Название товара, извлеченное из ценника';
COMMENT ON COLUMN recognitions.barcode IS 'Штрихкод товара';
COMMENT ON COLUMN recognitions.weight IS 'Вес или объем товара (например, 500г, 1л)';
COMMENT ON COLUMN recognitions.store IS 'Название магазина или торговой сети';
