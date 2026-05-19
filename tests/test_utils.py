import pandas as pd
from src.sentiment_thematic import assign_theme, extract_keyword_themes


def test_assign_theme_basic():
    assert assign_theme('The app crashes when I transfer money') == 'Crashes & Stability'
    assert assign_theme('Login failed, OTP not received') == 'Login & Access'
    assert assign_theme('Great UI and easy to use') == 'UI & UX'
    assert assign_theme('I want a budgeting feature') == 'Feature Requests'


def test_extract_keyword_themes():
    rows = [
        {'review': 'slow transfer and delay', 'bank': 'A'},
        {'review': 'transfer failed and slow', 'bank': 'A'},
        {'review': 'good app', 'bank': 'B'},
    ]
    df = pd.DataFrame(rows)
    kw = extract_keyword_themes(df, top_n=5)
    assert 'A' in kw and isinstance(kw['A'], list)
    assert len(kw['A']) <= 5
