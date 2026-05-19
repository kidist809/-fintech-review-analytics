"""Generate stakeholder-ready visualizations from processed data.

Produces images/ sentiment_by_bank.png, rating_distribution.png, and
top_keywords_by_bank.png. Reads `data/processed/reviews_processed.csv` or
falls back to `data/raw/reviews_clean.csv`.
"""
import os
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns


def load_processed():
    p = 'data/processed/reviews_processed.csv'
    if os.path.exists(p):
        return pd.read_csv(p)
    p2 = 'data/raw/reviews_clean.csv'
    if os.path.exists(p2):
        return pd.read_csv(p2)
    raise FileNotFoundError('No processed or clean CSV found. Run preprocessing first.')


def sentiment_by_bank(df: pd.DataFrame, out_dir='images'):
    os.makedirs(out_dir, exist_ok=True)
    counts = df.groupby(['bank', 'sentiment_label']).size().unstack(fill_value=0)
    ax = counts.plot(kind='bar', stacked=True, figsize=(8,5), colormap='viridis')
    plt.title('Sentiment Distribution by Bank')
    plt.ylabel('Number of Reviews')
    plt.xticks(rotation=0)
    plt.tight_layout()
    out = os.path.join(out_dir, 'sentiment_by_bank.png')
    plt.savefig(out)
    plt.close()
    print('Wrote', out)


def rating_distribution(df: pd.DataFrame, out_dir='images'):
    os.makedirs(out_dir, exist_ok=True)
    plt.figure(figsize=(8,5))
    sns.boxplot(data=df, x='bank', y='rating')
    plt.title('Rating Distribution per Bank')
    plt.tight_layout()
    out = os.path.join(out_dir, 'rating_distribution.png')
    plt.savefig(out)
    plt.close()
    print('Wrote', out)


def top_keywords_chart(keywords_csv: str = 'data/processed/top_keywords_by_bank.csv', out_dir='images'):
    if not os.path.exists(keywords_csv):
        print('Top keywords CSV not found:', keywords_csv)
        return
    os.makedirs(out_dir, exist_ok=True)
    df = pd.read_csv(keywords_csv)
    banks = df['bank'].unique()
    for bank in banks:
        sub = df[df['bank'] == bank].sort_values('rank').head(10)
        plt.figure(figsize=(8,5))
        plt.barh(sub['keyword'][::-1], sub['rank'][::-1])
        plt.title(f'Top Keywords — {bank}')
        plt.tight_layout()
        out = os.path.join(out_dir, f'top_keywords_{bank.replace(" ","_")}.png')
        plt.savefig(out)
        plt.close()
        print('Wrote', out)


def run_all():
    df = load_processed()
    sentiment_by_bank(df)
    rating_distribution(df)
    top_keywords_chart()


if __name__ == '__main__':
    run_all()
