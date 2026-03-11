from flask import Flask, render_template, request, redirect, session
import sqlite3
from model.recommender import recommend_books

app = Flask(__name__)
app.secret_key = "bookstore_secret"


def get_db():
    conn = sqlite3.connect("database/database.db")
    conn.row_factory = sqlite3.Row
    return conn


@app.route("/")
def index():

    conn = get_db()

    books = conn.execute(
        "SELECT * FROM books LIMIT 12"
    ).fetchall()

    categories = conn.execute(
        "SELECT DISTINCT category FROM books"
    ).fetchall()
    
    bestsellers = conn.execute(
        "SELECT * FROM books WHERE rating IS NOT NULL ORDER BY rating DESC LIMIT 8"
    ).fetchall()

    return render_template(
        "index.html",
        books=books,
        categories=categories,
        bestsellers=bestsellers
    )


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

    return render_template(
        "books.html",
        books=books,
        categories=categories
    )


@app.route("/book/<int:id>")
def book_detail(id):

    conn = get_db()

    book = conn.execute(
        "SELECT * FROM books WHERE id=?",
        (id,)
    ).fetchone()

    recommendations = recommend_books(book["title"])

    return render_template(
        "book_detail.html",
        book=book,
        recommendations=recommendations
    )


@app.route("/add_to_cart/<int:id>")
def add_to_cart(id):

    if "cart" not in session:
        session["cart"] = []

    session["cart"].append(id)

    session.modified = True

    return redirect("/cart")


@app.route("/cart")
def cart():

    conn = get_db()

    cart = session.get("cart", [])

    books = []

    for id in cart:
        book = conn.execute(
            "SELECT * FROM books WHERE id=?",
            (id,)
        ).fetchone()
        books.append(book)

    total = sum(book["price"] for book in books)

    return render_template(
        "cart.html",
        books=books,
        total=total
    )


@app.route("/checkout")
def checkout():

    session["cart"] = []

    return render_template("checkout.html")


@app.route("/dashboard")
def dashboard():

    conn = get_db()
    total_books = conn.execute(
            "SELECT COUNT(*) FROM books"
    ).fetchone()[0]

    return render_template( "dashboard.html",total_books=total_books)

@app.route("/blog")
def blog():

    posts = [
        {
            "title": "Top 10 Best Business Books",
            "content": "Discover the most popular business books..."
        },
        {
            "title": "Best Machine Learning Books",
            "content": "Recommended ML books for beginners."
        }
    ]

    return render_template("blog.html", posts=posts)


if __name__ == "__main__":
    app.run(debug=True)