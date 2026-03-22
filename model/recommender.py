import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


# --------------------------
# LOAD DATASET
# --------------------------

df = pd.read_excel("dataset/books_clean.xlsx")

df["content"] = df["content"].fillna("")


# --------------------------
# TF-IDF MODEL
# --------------------------

tfidf = TfidfVectorizer(stop_words="english")

tfidf_matrix = tfidf.fit_transform(df["content"])


# --------------------------
# COSINE SIMILARITY
# --------------------------

cosine_sim = cosine_similarity(tfidf_matrix, tfidf_matrix)


# --------------------------
# INDEX MAPPING
# --------------------------

indices = pd.Series(df.index, index=df["title"]).drop_duplicates()


# --------------------------
# RECOMMEND FUNCTION
# --------------------------

def recommend_books(title, top_n=5):

    if title not in indices:
        return []

    idx = indices[title]

    sim_scores = list(enumerate(cosine_sim[idx]))

    sim_scores = sorted(
        sim_scores,
        key=lambda x: x[1],
        reverse=True
    )

    sim_scores = sim_scores[1:top_n+1]

    book_indices = [i[0] for i in sim_scores]

    recommendations = df.iloc[book_indices][
        ["id", "title", "author", "price", "rating", "image", "category"]
    ]

    return recommendations.to_dict("records")

def recommend_for_user_db(user_id, conn, top_n=10):

    rows = conn.execute("""
        SELECT b.title, b.category, ub.action
        FROM user_behavior ub
        JOIN books b ON ub.book_id = b.id
        WHERE ub.user_id = ?
    """, (user_id,)).fetchall()

    if not rows:
        return []

    from collections import Counter

    titles = []
    category_score = Counter()

    # 🎯 GÁN TRỌNG SỐ HÀNH VI
    for r in rows:
        titles.append(r["title"])

        if r["action"] == "view":
            category_score[r["category"]] += 1
        elif r["action"] == "cart":
            category_score[r["category"]] += 3   # mạnh hơn

    rec_pool = []

    for t in titles:
        rec_pool += recommend_books(t)

    # loại trùng
    seen = set()
    results = []

    for r in rec_pool:
        if r["id"] not in seen:
            r["score"] = category_score.get(r["category"], 0)
            results.append(r)
            seen.add(r["id"])

    # 🎯 boost favorite_category
    user = conn.execute(
        "SELECT favorite_category FROM users WHERE id=?",
        (user_id,)
    ).fetchone()

    if user and user["favorite_category"]:
        for r in results:
            if r["category"] == user["favorite_category"]:
                r["score"] += 2

    results = sorted(results, key=lambda x: x["score"], reverse=True)

    return results[:top_n]