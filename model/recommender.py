import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# load dataset
df = pd.read_excel("dataset/books_clean.xlsx")

# TF-IDF
tfidf = TfidfVectorizer(stop_words="english")

tfidf_matrix = tfidf.fit_transform(df["content"].fillna(""))

# cosine similarity
cosine_sim = cosine_similarity(tfidf_matrix, tfidf_matrix)

# index theo title
indices = pd.Series(df.index, index=df["title"]).drop_duplicates()


def recommend_books(title, top_n=5):

    if title not in indices:
        return []

    idx = indices[title]

    sim_scores = list(enumerate(cosine_sim[idx]))

    sim_scores = sorted(sim_scores, key=lambda x: x[1], reverse=True)

    sim_scores = sim_scores[1:top_n+1]

    book_indices = [i[0] for i in sim_scores]

    return df.iloc[book_indices].to_dict("records")