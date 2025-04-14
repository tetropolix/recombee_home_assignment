
CREATE TABLE IF NOT EXISTS feed_items(
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    link TEXT NOT NULL,
    image_link TEXT,
    additional_image_link TEXT[],
    price TEXT,
    condition TEXT,
    availability TEXT,
    brand TEXT,
    gtin TEXT,
    item_group_id TEXT,
    sale_price TEXT
);

CREATE TABLE IF NOT EXISTS feed_uploads (
    id SERIAL PRIMARY KEY,
    status INTEGER NOT NULL CHECK (status IN (1, 2, 3, 4)),
    error TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);