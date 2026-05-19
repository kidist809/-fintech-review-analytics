"""Sentiment and Thematic Analysis pipeline

Loads `data/raw/reviews_clean.csv`, applies a transformer sentiment model
and a TF-IDF based keyword extractor, assigns simple themes, and writes
`data/processed/reviews_processed.csv` with added columns.
"""
from transformers import pipeline
import pandas as pd
import os
from sklearn.feature_extraction.text import TfidfVectorizer
from typing import List, Dict


def load_clean(path: str = 'data/raw/reviews_clean.csv') -> pd.DataFrame:
    return pd.read_csv(path)


def sentiment_transformer(texts: List[str], model_name: str = 'distilbert-base-uncased-finetuned-sst-2-english') -> List[Dict]:
    """Return list of dicts with label and score for each text."""
    nlp = pipeline('sentiment-analysis', model=model_name)
    results = nlp(texts, truncation=True)
    transformed = []
    for r in results:
        label = r.get('label', '')
        score = float(r.get('score', 0.0))
        # Map SST-2 outputs to positive/negative/neutral
        if score >= 0.60:
            if label.upper().startswith('POS'):
                sentiment = 'positive'
            else:
                sentiment = 'negative'
        else:
            sentiment = 'neutral'
        transformed.append({'sentiment_label': sentiment, 'sentiment_score': score})
    return transformed


def extract_keyword_themes(df: pd.DataFrame, top_n: int = 20) -> Dict[str, List[str]]:
    """Compute top TF-IDF n-grams per bank and return dict(bank -> keywords).
    Also writes a CSV `data/processed/top_keywords_by_bank.csv`.
    """
    os.makedirs('data/processed', exist_ok=True)
    banks = df['bank'].unique()
    vec = TfidfVectorizer(stop_words='english', ngram_range=(1,2), max_features=2000)
    kw_by_bank = {}
    for bank in banks:
        texts = df.loc[df['bank'] == bank, 'review'].astype(str).tolist()
        if not texts:
            kw_by_bank[bank] = []
            continue
        X = vec.fit_transform(texts)
        # get mean tfidf per term
        import numpy as np
        mean_tfidf = np.asarray(X.mean(axis=0)).ravel()
        terms = vec.get_feature_names_out()
        top_idx = mean_tfidf.argsort()[::-1][:top_n]
        top_terms = [terms[i] for i in top_idx]
        kw_by_bank[bank] = top_terms

    # save to csv
    rows = []
    for bank, kws in kw_by_bank.items():
        for rank, kw in enumerate(kws, start=1):
            rows.append({'bank': bank, 'rank': rank, 'keyword': kw})
    pd.DataFrame(rows).to_csv('data/processed/top_keywords_by_bank.csv', index=False)
    return kw_by_bank


THEME_KEYWORDS = {
    'Transaction Performance': ['slow', 'delay', 'transfer', 'loading', 'timeout', 'lag'],
    'Login & Access': ['login', 'otp', 'password', 'pin', 'biometric', 'fingerprint'],
    'Crashes & Stability': ['crash', 'error', 'exception', 'hang', 'freeze', 'bug'],
    'UI & UX': ['ui', 'interface', 'navigation', 'design', 'layout', 'easy to use'],
    'Customer Support': ['support', 'customer', 'service', 'help', 'response', 'agent'],
    'Feature Requests': ['feature', 'request', 'add', 'integration', 'budget', 'report']
}


def assign_theme(text: str) -> str:
    t = str(text).lower()
    for theme, keywords in THEME_KEYWORDS.items():
        for kw in keywords:
            if kw in t:
                return theme
    return 'Other'


def run_pipeline(input_path: str = 'data/raw/reviews_clean.csv', output_path: str = 'data/processed/reviews_processed.csv') -> pd.DataFrame:
    df = load_clean(input_path)
    # Sentiment
    print('Running transformer sentiment analysis...')
    texts = df['review'].astype(str).tolist()
    sent = sentiment_transformer(texts)
    df['sentiment_label'] = [s['sentiment_label'] for s in sent]
    df['sentiment_score'] = [s['sentiment_score'] for s in sent]

    # Themes via keywords
    print('Extracting top keywords per bank...')
    kw_by_bank = extract_keyword_themes(df, top_n=30)
    print('Assigning themes to each review (rule-based)...')
    df['identified_theme'] = df['review'].apply(assign_theme)

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    df.to_csv(output_path, index=False)
    print(f'Wrote processed file: {output_path}')
    return df


if __name__ == '__main__':
    run_pipeline()
