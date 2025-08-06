import pandas as pd
import glob
import os

CROP_THRESHOLDS: dict[str, dict] = {
    "tea": {
        "icon": "🌱",
        "min_temp": 13,
        "max_temp": 25,
        "min_precip": 400,
        "max_precip": 800,
        "min_humidity": 70,
        "max_humidity": 90,
        "min_solarradiation": 10,
        "max_solarradiation": 20
    },
    "coffee": {
        "icon": "",
        "min_temp": 15,
        "max_temp": 24,
        "min_precip": 300,
        "max_precip": 600,
        "min_humidity": 60,
        "max_humidity": 80,
        "min_solarradiation": 12,
        "max_solarradiation": 22
    },
    "wheat": {
        "icon": "🌾",
        "min_temp": 15,
        "max_temp": 20,
        "min_precip": 300,
        "max_precip": 900,
        "min_humidity": 50,
        "max_humidity": 60,
        "min_solarradiation": 14,
        "max_solarradiation": 25
    },
    "bananas": {
        "icon": "🍌",
        "min_temp": 20,
        "max_temp": 30,
        "min_precip": 500,
        "max_precip": 900,
        "min_humidity": 60,
        "max_humidity": 90,
        "min_solarradiation": 14,
        "max_solarradiation": 25
    },
    "rice": {
        "icon": "🌾",
        "min_temp": 20,
        "max_temp": 35,
        "min_precip": 600,
        "max_precip": 1200,
        "min_humidity": 70,
        "max_humidity": 90,
        "min_solarradiation": 14,
        "max_solarradiation": 26
    },
    "maize": {
        "icon": "🌽",
        "min_temp": 18,
        "max_temp": 30,
        "min_precip": 400,
        "max_precip": 700,
        "min_humidity": 50,
        "max_humidity": 80,
        "min_solarradiation": 15,
        "max_solarradiation": 27
    },
    "beans": {
        "icon": "🫘",
        "min_temp": 15,
        "max_temp": 27,
        "min_precip": 300,
        "max_precip": 600,
        "min_humidity": 50,
        "max_humidity": 80,
        "min_solarradiation": 13,
        "max_solarradiation": 24
    },
    "sukuma_wiki": {
        "icon": "🥬",
        "min_temp": 15,
        "max_temp": 28,
        "min_precip": 300,
        "max_precip": 700,
        "min_humidity": 55,
        "max_humidity": 85,
        "min_solarradiation": 13,
        "max_solarradiation": 24
    }
}

def load_weather_data(folder_path) -> pd.DataFrame:
    print("Loading weather data...")

    csv_files = glob.glob(os.path.join(folder_path, "*.csv"))
    if not csv_files:
        print(f"No CSV files found in {folder_path}. Returning an empty DataFrame.")
        return pd.DataFrame()

    df_list = []
    for file in csv_files:
        print(f"Loading file {file}")
        df_list.append(pd.read_csv(file, index_col="datetime"))

    weather = pd.concat(df_list, axis=0)
    weather.index = pd.to_datetime(weather.index)

    # Group weather conditions
    # Clean conditions column
    weather["conditions"] = weather.apply(group_weather_conditions, axis=1)
    weather = clean_string_column(weather.copy(), "conditions")
    weather = clean_string_column(weather.copy(), "name")

    # Group weather data into seasons
    weather = group_seasons(weather)
    return weather

def group_weather_conditions(row):
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

def get_season(month):
    if month in [1, 2, 3]:
        return "JFM"    # January, February, March season
    elif month in [4, 5, 6]:
        return "AMJ"    # April, May, June season
    elif month in [7, 8, 9]:
        return "JAS"    # July, August, September season
    else:
        return "OND"    # October, November, December season

def group_seasons(weather):
    weather["year"] = weather.index.year
    weather["month"] = weather.index.month
    weather["season"] = weather["month"].apply(get_season)
    return weather

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