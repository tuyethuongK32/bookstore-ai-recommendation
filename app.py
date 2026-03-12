from flask import Flask, render_template, request, redirect, session, flash
import sqlite3
from model.recommender import recommend_books
from collections import Counter
import math
import random

app = Flask(__name__)
app.secret_key = "bookstore_secret"


# ---------------------------
# DATABASE CONNECTION
# ---------------------------
def get_db():
    conn = sqlite3.connect("database/database.db")
    conn.row_factory = sqlite3.Row
    return conn


# ---------------------------
# HOME PAGE
# ---------------------------
@app.route("/")
def index():

    conn = get_db()

    books = conn.execute(
        "SELECT * FROM books LIMIT 12"
    ).fetchall()

    categories = conn.execute(
        "SELECT DISTINCT category FROM books limit 40"
    ).fetchall()

    bestsellers = conn.execute(
        "SELECT * FROM books WHERE rating IS NOT NULL ORDER BY rating DESC LIMIT 12"
    ).fetchall()

    # AI recommendation cho homepage
    try:
        random_book = random.choice(books)
        recommendations = recommend_books(random_book["title"])
    except:
        recommendations = []

    featured = books[:12]

    conn.close()

    return render_template(
        "index.html",
        books=books,
        categories=categories,
        bestsellers=bestsellers,
        recommendations=recommendations,
        featured=featured
    )


# ---------------------------
# BOOK LIST
# ---------------------------
@app.route("/books")
def books():

    conn = get_db()

    search = request.args.get("search")
    category = request.args.get("category")
    sort = request.args.get("sort")

    page = int(request.args.get("page", 1))
    per_page = 12
    offset = (page - 1) * per_page

    query = "SELECT * FROM books WHERE 1=1"
    params = []

    if search:
        query += " AND title LIKE ?"
        params.append("%" + search + "%")

    if category:
        query += " AND category=?"
        params.append(category)

    if sort == "price_asc":
        query += " ORDER BY price ASC"

    elif sort == "price_desc":
        query += " ORDER BY price DESC"

    # tổng số sách
    count_query = query.replace("SELECT *", "SELECT COUNT(*)")

    total_books = conn.execute(count_query, params).fetchone()[0]

    total_pages = (total_books // per_page) + (1 if total_books % per_page else 0)

    # pagination
    query += " LIMIT ? OFFSET ?"
    params.extend([per_page, offset])

    books = conn.execute(query, params).fetchall()

    categories = conn.execute(
        "SELECT DISTINCT category FROM books"
    ).fetchall()

    conn.close()

    return render_template(
        "books.html",
        books=books,
        categories=categories,
        page=page,
        total_pages=total_pages
    )


# ---------------------------
# BOOK DETAIL
# ---------------------------
@app.route("/book/<int:id>")
def book_detail(id):

    conn = get_db()

    book = conn.execute(
        "SELECT * FROM books WHERE id=?",
        (id,)
    ).fetchone()

    if not book:
        return "Book not found"

    try:
        recommendations = recommend_books(book["title"])
    except:
        recommendations = []
        
    # track view
    if "views" not in session:
        session["views"] = {}

    views = session["views"]
    views[str(id)] = views.get(str(id), 0) + 1
    session["views"] = views

    conn.close()

    return render_template(
        "book_detail.html",
        book=book,
        recommendations=recommendations
    )


# ---------------------------
# ADD TO CART
# ---------------------------
@app.route("/add_to_cart/<int:id>")
def add_to_cart(id):

    if "cart" not in session:
        session["cart"] = []

    session["cart"].append(id)
    session.modified = True

    flash("Đã thêm sách vào giỏ hàng!")

    return redirect("/cart")


# ---------------------------
# REMOVE FROM CART
# ---------------------------
@app.route("/remove_from_cart/<int:id>")
def remove_from_cart(id):

    cart = session.get("cart", [])

    if id in cart:
        cart.remove(id)

    session["cart"] = cart
    session.modified = True

    return redirect("/cart")


# ---------------------------
# CART PAGE
# ---------------------------
@app.route("/cart")
def cart():

    cart = session.get("cart", [])

    conn = get_db()

    books = []

    for book_id in cart:

        book = conn.execute(
            "SELECT * FROM books WHERE id=?",
            (book_id,)
        ).fetchone()

        books.append(book)

    counts = Counter(cart)

    total = 0

    unique_books = {}

    for book in books:
        unique_books[book["id"]] = book

        total = sum(
        book["price"] * counts.get(book["id"], 0)
           for book in unique_books.values()
        )
    # AI recommend dựa trên sách trong giỏ hàng
    recommendations = []

    try:
       titles = [b["title"] for b in books]           # tiêu đề các sách trong cart
       rec_pool = []

       for t in titles:
        rec_pool += recommend_books(t)             # gợi ý cho từng sách

        # loại bỏ sách đã có trong cart
        cart_ids = {b["id"] for b in books}
        rec_pool = [r for r in rec_pool if r["id"] not in cart_ids]

         # lấy tối đa 8 sách gợi ý
        recommendations = rec_pool[:8]

    except:
        recommendations = []
        
    conn.close()

    return render_template(
        "cart.html",
        books=books,
        counts=counts,
        total=total,
        recommendations=recommendations
    )


# ---------------------------
# CHECKOUT
# ---------------------------
@app.route("/checkout", methods=["GET", "POST"])
def checkout():

    cart = session.get("cart", [])

    conn = get_db()

    books = []

    for book_id in cart:
        book = conn.execute(
            "SELECT * FROM books WHERE id=?",
            (book_id,)
        ).fetchone()
        books.append(book)

    counts = Counter(cart)

    total = 0
    for book in books:
        total += book["price"] * counts[book["id"]]

    conn.close()

    if request.method == "POST":

        name = request.form["name"]
        phone = request.form["phone"]
        address = request.form["address"]

        # demo: xóa giỏ hàng
        session["cart"] = []

        return render_template(
            "checkout.html",
            success=True,
            total=total
        )

    return render_template(
        "checkout.html",
        success=False,
        total=total
    )


# ---------------------------
# ADMIN DASHBOARD
# ---------------------------
@app.route("/dashboard")
def dashboard():

    conn = get_db()

    total_books = conn.execute(
        "SELECT COUNT(*) FROM books"
    ).fetchone()[0]

    # demo: tổng đơn hàng (tạm tính theo cart)
    total_orders = len(session.get("cart", []))

    # demo: lượt xem sách
    views = session.get("views", {})

    # lấy top 5 sách được xem nhiều nhất
    top_books = sorted(
        views.items(),
        key=lambda x: x[1],
        reverse=True
    )[:5]

    top_book_ids = [int(v[0]) for v in top_books]

    top_view_books = []

    if top_book_ids:
        placeholders = ",".join(["?"] * len(top_book_ids))
        query = f"SELECT * FROM books WHERE id IN ({placeholders})"
        top_view_books = conn.execute(query, top_book_ids).fetchall()

    conn.close()

    return render_template(
        "dashboard.html",
        total_books=total_books,
        total_orders=total_orders,
        top_view_books=top_view_books
    )

# ---------------------------
# BLOG PAGE (MARKETING)
# ---------------------------
@app.route("/blog")
def blog():

    conn = get_db()

    literature = conn.execute(
        "SELECT * FROM books WHERE category LIKE '%Văn học%' LIMIT 3"
    ).fetchall()

    psychology = conn.execute(
        "SELECT * FROM books WHERE category LIKE '%Tâm%' LIMIT 3"
    ).fetchall()

    children = conn.execute(
        "SELECT * FROM books WHERE category LIKE '%Truyện tranh%' LIMIT 3"
    ).fetchall()

    education = conn.execute(
        "SELECT * FROM books WHERE category LIKE '%Giáo dục%' LIMIT 3"
    ).fetchall()

    conn.close()

    literature = [dict(x) for x in literature]
    psychology = [dict(x) for x in psychology]
    children = [dict(x) for x in children]
    education = [dict(x) for x in education]

    return render_template(
        "blog.html",
        literature=literature,
        psychology=psychology,
        children=children,
        education=education
    )

# ---------------------------
# RUN APP
# ---------------------------
if __name__ == "__main__":
    app.run(debug=True)