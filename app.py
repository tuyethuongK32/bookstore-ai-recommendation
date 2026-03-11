from flask import Flask, render_template, request, redirect, session, flash
import sqlite3
from model.recommender import recommend_books
from collections import Counter

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
    
    featured = books[:8]
    recommendations = books[8:16]
    

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

    books = conn.execute(query, params).fetchall()

    categories = conn.execute(
        "SELECT DISTINCT category FROM books"
    ).fetchall()

    conn.close()

    return render_template(
        "books.html",
        books=books,
        categories=categories
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

    for book in books:
        total += book["price"]

    return render_template(
        "cart.html",
        books=books,
        counts=counts,
        total=total
    )


# ---------------------------
# CHECKOUT
# ---------------------------
@app.route("/checkout", methods=["GET", "POST"])
def checkout():

    if request.method == "POST":

        name = request.form["name"]
        phone = request.form["phone"]
        address = request.form["address"]

        # demo: xóa giỏ hàng sau khi đặt
        session["cart"] = []

        return render_template(
            "checkout.html",
            success=True
        )

    return render_template(
        "checkout.html",
        success=False
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

    total_orders = len(session.get("cart", []))

    total_users = 10  # demo

    return render_template(
        "dashboard.html",
        total_books=total_books,
        total_orders=total_orders,
        total_users=total_users
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