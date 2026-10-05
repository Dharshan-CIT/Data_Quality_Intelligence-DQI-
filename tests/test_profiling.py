from dqi_core.profiling import profile_dataset


def test_row_and_column_counts(messy_df):
    profile = profile_dataset(messy_df, "messy")
    assert profile.rows == 8
    assert profile.columns == 5


def test_null_count(messy_df):
    profile = profile_dataset(messy_df, "messy")
    assert profile.column_profiles["price"].null_count == 2


def test_duplicate_count(messy_df):
    profile = profile_dataset(messy_df, "messy")
    assert profile.duplicate_rows == 1  # row index 3 and 4 are identical


def test_datatype_detection(messy_df):
    profile = profile_dataset(messy_df, "messy")
    assert "price" in profile.numeric_columns
    assert "category" in profile.categorical_columns
