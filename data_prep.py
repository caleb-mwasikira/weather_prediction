import pandas as pd

def load_weather_data() -> pd.DataFrame:
    print("Loading weather data...\n")
    weather_2020 = pd.read_csv("./weather_data/Kericho, Kenya 2020-01-01 to 2020-12-31.csv", index_col="datetime")
    weather_2021 = pd.read_csv("./weather_data/Kericho, Kenya 2021-01-01 to 2021-12-31.csv", index_col="datetime")
    weather_2022 = pd.read_csv("./weather_data/Kericho, Kenya 2022-01-01 to 2022-12-31.csv", index_col="datetime")
    weather_2023 = pd.read_csv("./weather_data/Kericho, Kenya 2023-01-01 to 2023-12-31.csv", index_col="datetime")
    weather_2024 = pd.read_csv("./weather_data/Kericho, Kenya 2024-01-01 to 2024-12-31.csv", index_col="datetime")

    weather = pd.concat([weather_2020,weather_2021,weather_2022,weather_2023,weather_2024], axis=0)
    
    weather.index = pd.to_datetime(weather.index)
    weather["conditions"] = weather.apply(classify_weather, axis=1)
    weather = clean_string_column(weather.copy(), "conditions")
       
    return weather

def classify_weather(row):
    if row["precip"] > 4.0:
        return "rain"
    elif row["cloudcover"] > 80:
        return "overcast"
    elif row["cloudcover"] < 15 and row["solarradiation"] > 500:
        return "sunny"
    elif row["cloudcover"] > 40 or row["humidity"] > 70:
        return "partially_cloudy"
    else:
        return "clear"

def clean_string_column(df, column_name):
    """
    Reformats a string column in a Pandas DataFrame:
    - Removes all whitespace.
    - Removes all commas.
    - Converts to lowercase.
    - Replaces remaining spaces (if any after initial cleanup) with underscores.

    Args:
        df (pd.DataFrame): The input DataFrame.
        column_name (str): The name of the column to clean.

    Returns:
        pd.DataFrame: The DataFrame with the cleaned column.
    """
    # Ensure the column is of string type to apply string methods
    column = df[column_name].astype(str)

    column = column.str.replace(' ', '_', regex=True)
    column = column.str.replace(',', '')
    column = column.str.lower()

    df[column_name] = column
    return df