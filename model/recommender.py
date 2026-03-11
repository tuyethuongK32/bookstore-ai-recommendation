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