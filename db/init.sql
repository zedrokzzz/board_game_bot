CREATE TABLE search_info (
    id SERIAL PRIMARY KEY,
    title TEXT NOT NULL,
    price NUMERIC,
    link TEXT NOT NULL,
    rating FLOAT,
    players TEXT,
    time TEXT,
    age TEXT,
    is_popular BOOLEAN,
    comments_count INTEGER
);
