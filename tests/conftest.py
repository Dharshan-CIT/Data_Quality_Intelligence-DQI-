import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import pandas as pd
import pytest


@pytest.fixture
def messy_df():
    df = pd.DataFrame({
        "id": [1, 2, 3, 4, 4, 6, 7, 8],
        "price": [10.0, -5.0, 20.0, np.nan, np.nan, 15.0, 0.0, 1000.0],
        "quantity": [1, 2, 3, 4, 4, 5, 6, 7],
        "category": ["A", "a", " A ", "B", "B", "b", "C", "C"],
        "signup_date": ["2024-01-01", "2024-02-01", "not-a-date", "2024-03-01",
                         "2024-03-01", "2024-04-01", "2024-05-01", "2030-01-01"],
    })
    return df
