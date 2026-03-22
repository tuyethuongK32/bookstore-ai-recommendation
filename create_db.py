import sqlite3
import pandas as pd


# đọc dataset excel
df = pd.read_excel("dataset/books_clean.xlsx")

conn = sqlite3.connect("database/database.db")
cursor = conn.cursor()

cursor.executescript("""
CREATE TABLE IF NOT EXISTS books (
    id INTEGER PRIMARY KEY,
    title TEXT,
    author TEXT,
    price REAL,
    category TEXT,
    rating REAL,
    image TEXT,
    content TEXT
);

CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE,
    password TEXT,
    full_name TEXT,
    email TEXT,
    favorite_category TEXT
);

CREATE TABLE IF NOT EXISTS user_behavior (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    book_id INTEGER,
    action TEXT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
);
""")


# xóa dữ liệu cũ (tránh insert trùng)
cursor.execute("DELETE FROM books")

for _, row in df.iterrows():

    cursor.execute("""
    INSERT INTO books
    (id, title, author, price, category, rating, image, content)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (

        int(row["id"]),
        row["title"],
        row["author"],
        float(row["price"]),
        row["category"],
        float(row["rating"]),
        row["image"],
        row["content"]
    ))

# -------------------------
# CREATE INDEX (tăng tốc search)
# -------------------------

cursor.execute("CREATE INDEX IF NOT EXISTS idx_title ON books(title)")
# cursor.execute("CREATE INDEX IF NOT EXISTS idx_category ON books(category)")


# -------------------------
# COMMIT
# -------------------------

conn.commit()
conn.close()

print("Database created successfully!")
print("Total books:", len(df))