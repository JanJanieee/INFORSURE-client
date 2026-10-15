"""Traditional candidates (thesis section 13.5): Linear SVM and Naive Bayes on TF-IDF."""
from backend.app.pipeline.prediction import predict_with_confidence
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.naive_bayes import MultinomialNB
from sklearn.pipeline import Pipeline
from sklearn.svm import LinearSVC


def _tfidf(cfg: dict) -> TfidfVectorizer:
    t = cfg["tfidf"]
    return TfidfVectorizer(
        ngram_range=tuple(t["ngram_range"]), min_df=t["min_df"], max_features=t["max_features"]
    )


def build_svm(cfg: dict) -> Pipeline:
    return Pipeline([
        ("tfidf", _tfidf(cfg)),
        ("clf", LinearSVC(C=cfg["svm"]["C"], class_weight=cfg["svm"]["class_weight"], random_state=cfg["seed"])),
    ])


def build_nb(cfg: dict) -> Pipeline:
    return Pipeline([("tfidf", _tfidf(cfg)), ("clf", MultinomialNB(alpha=cfg["nb"]["alpha"]))])


CANDIDATES = {"svm": build_svm, "nb": build_nb}
