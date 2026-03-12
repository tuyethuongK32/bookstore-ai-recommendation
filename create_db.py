import sqlite3
import pandas as pd


# đọc dataset excel
df = pd.read_excel("dataset/books_clean.xlsx")

conn = sqlite3.connect("database/database.db")
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS books (
    id INTEGER PRIMARY KEY,
    title TEXT,
    author TEXT,
    price REAL,
    category TEXT,
    rating REAL,
    image TEXT,
    content TEXT
)
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