from flask import Flask, render_template, request, redirect, session, flash
import sqlite3
from model.recommender import recommend_books
from collections import Counter
import math
import random
from werkzeug.security import generate_password_hash, check_password_hash
from model.recommender import recommend_for_user_db

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
    recent_books = []
    try:
        if "user_id" in session:
            recent_books = conn.execute("""
                SELECT DISTINCT b.*
                FROM user_behavior ub
                JOIN books b ON ub.book_id = b.id
                WHERE ub.user_id = ?
                ORDER BY ub.timestamp DESC
                LIMIT 8
            """, (session["user_id"],)).fetchall()

            if recent_books:
                # Lấy title sách gần đây nhất để gợi ý
                recommendations = recommend_books(recent_books[0]["title"])
            elif books:
                recommendations = recommend_books(random.choice(books)["title"])
        elif books:
            recommendations = recommend_books(random.choice(books)["title"])
    except Exception as e:
        recommendations = []

    featured = books[:12]

    conn.close()

    return render_template(
        "index.html",
        books=books,
        categories=categories,
        bestsellers=bestsellers,
        recommendations=recommendations,
        featured=featured,
        recent_books=recent_books
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
    
    if "user_id" in session:
       save_behavior(session["user_id"], id, "view")

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
    
    if "user_id" in session:
      save_behavior(session["user_id"], id, "cart")

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
          rec_pool += recommend_books(t)

       # lọc sau khi gom xong
       cart_ids = {b["id"] for b in books}
       rec_pool = [r for r in rec_pool if r["id"] not in cart_ids]

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
    
#----------------------------
# Register
#-----------------------------
@app.route("/register", methods=["GET", "POST"])
def register():
    conn = get_db()

    categories = conn.execute(
        "SELECT DISTINCT category FROM books"
    ).fetchall()

    if request.method == "POST":
        username = request.form.get("username")
        password_raw = request.form.get("password")
        full_name = request.form.get("full_name")
        email = request.form.get("email")
        favorite_category = request.form.get("favorite_category")

        # ✅ Validate cơ bản
        if not username or not password_raw:
            flash("Vui lòng nhập đầy đủ thông tin")
            conn.close()
            return render_template("register.html", categories=categories)

        password = generate_password_hash(password_raw)

        try:
            conn.execute(
                """INSERT INTO users 
                (username, password, full_name, email, favorite_category) 
                VALUES (?, ?, ?, ?, ?)""",
                (username, password, full_name, email, favorite_category)
            )
            conn.commit()

            # ✅ AUTO LOGIN (KHÔNG redirect login nữa)
            user_id = conn.execute(
                "SELECT last_insert_rowid()"
            ).fetchone()[0]

            session["user_id"] = user_id
            session["username"] = username

            flash("Đăng ký thành công 🎉")
            conn.close()

            return redirect("/")   # 👉 về trang chủ luôn

        except:
            flash("Username đã tồn tại")

    conn.close()
    return render_template("register.html", categories=categories)

#---------------------------
# Login
#---------------------------
@app.route("/login", methods=["GET", "POST"])
def login():
    conn = get_db()
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        user = conn.execute(
            "SELECT * FROM users WHERE username=?",
            (username,)
        ).fetchone()

        if user and check_password_hash(user["password"], password):
            session["user_id"] = user["id"]
            session["username"] = user["username"]
            flash("Đăng nhập thành công")
            conn.close()
            return redirect("/")
        else:
            flash("Sai thông tin")

    conn.close()
    return render_template("login.html")

#--------------------------
# Logout
#---------------------------
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

#---------------------------
# Click
#--
@app.route("/click/<int:id>")
def track_click(id):
    if "user_id" in session:
        save_behavior(session["user_id"], id, "click")
    return redirect(f"/book/{id}")


#----------------------------
# History
#----------------------------
# ---------------------------
# USER HISTORY
# ---------------------------
@app.route("/history")
def history():

    if "user_id" not in session:
        return redirect("/login")

    conn = get_db()

    rows = conn.execute("""
        SELECT b.*, ub.action, ub.timestamp
        FROM user_behavior ub
        JOIN books b ON ub.book_id = b.id
        WHERE ub.user_id = ?
        ORDER BY ub.timestamp DESC
        LIMIT 20
    """, (session["user_id"],)).fetchall()

    conn.close()

    return render_template("history.html", histories=rows)

def save_behavior(user_id, book_id, action):
    conn = get_db()

    conn.execute(
        "INSERT INTO user_behavior (user_id, book_id, action) VALUES (?, ?, ?)",
        (user_id, book_id, action)
    )

    # 🎯 UPDATE FAVORITE CATEGORY
    conn.execute("""
        UPDATE users
        SET favorite_category = (
            SELECT b.category
            FROM user_behavior ub
            JOIN books b ON ub.book_id = b.id
            WHERE ub.user_id = ?
            GROUP BY b.category
            ORDER BY COUNT(*) DESC
            LIMIT 1
        )
        WHERE id = ?
    """, (user_id, user_id))

    conn.commit()
    conn.close()

# ---------------------------
# RUN APP
# ---------------------------
if __name__ == "__main__":
    app.run(debug=True)