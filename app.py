from flask import Flask, jsonify, request
import pandas as pd
from datetime import datetime, timedelta

app = Flask(__name__)

PLANT_THRESHOLDS = {
    "tea": {
        "min_temp": 15,
        "max_temp": 25,
        "min_precip": 12,
        "max_precip": 15,
        "humidity": 60,
    },
    "coffee": {
        "min_temp": 18,
        "max_temp": 24,
        "min_precip": 15,
        "max_precip": 20,
        "humidity": 50,
        "altitude": (100, 800),
    },
    # "coffee/arabica": {
    #     "min_temp": 18,
    #     "max_temp": 24,
    #     "min_precip": 15,
    #     "max_precip": 20,
    #     "humidity": 50,
    #     "altitude": (100, 800),
    # },
    # "coffee/robusta": {
    #     "min_temp": 24,
    #     "max_temp": 30,
    #     "min_precip": 20,
    #     "max_precip": 30,
    #     "humidity": 50,
    #     "altitude": (180, 760),
    # }
}

def classify_weather(row):
    if row["precip"] > 2.0:
        return "Rain"
    elif row["cloudcover"] > 80:
        return "Overcast"
    elif row["cloudcover"] < 15 and row["solarradiation"] > 500:
        return "Sunny"
    elif row["cloudcover"] > 40 or row["humidity"] > 70:
        return "Partially cloudy"
    else:
        return "Clear"

def load_weather_data() -> pd.DataFrame:
    print("Loading weather data...\n")
    weather_2020 = pd.read_csv("./weather_data/Kericho, Kenya 2020-01-01 to 2020-12-31.csv", index_col="datetime")
    weather_2021 = pd.read_csv("./weather_data/Kericho, Kenya 2021-01-01 to 2021-12-31.csv", index_col="datetime")
    weather_2022 = pd.read_csv("./weather_data/Kericho, Kenya 2022-01-01 to 2022-12-31.csv", index_col="datetime")
    weather_2023 = pd.read_csv("./weather_data/Kericho, Kenya 2023-01-01 to 2023-12-31.csv", index_col="datetime")
    weather_2024 = pd.read_csv("./weather_data/Kericho, Kenya 2024-01-01 to 2024-12-31.csv", index_col="datetime")

    weather = pd.concat([weather_2020,weather_2021,weather_2022,weather_2023,weather_2024], axis=0)
    weather.index = pd.to_datetime(weather.index)
    
    # Reformat weather conditions    
    weather["conditions"] = weather.apply(classify_weather, axis=1)    
    return weather

weather = load_weather_data()

def get_recommendations(weather, my_plant):
    if my_plant not in PLANT_THRESHOLDS:
        return {"error": f"Unsupported plant {my_plant}"}

    avg_temp = weather['temp'].mean()
    avg_precip = weather['precip'].mean()
    avg_humidity = weather['humidity'].mean()
    avg_solar = weather['solarradiation'].mean()
    
    threshold = PLANT_THRESHOLDS[my_plant]
    plant_min_temp = threshold["min_temp"]
    plant_min_precip = threshold["min_precip"] 
    plant_max_precip = threshold["max_precip"]
    
    optimum_temp = (avg_temp / plant_min_temp) >= 0.6
    high_rainfall = (avg_precip / plant_min_precip) >= 0.6

    recommendations = []
    
    # Check planting conditions
    if optimum_temp and high_rainfall:
        recommendations.append(f"Good conditions to plant {my_plant}.")
    
    # Check irrigation conditions
    low_rainfall = (avg_precip / plant_min_precip) < 0.5
    high_rainfall = (avg_precip / plant_max_precip) > 0.5
    if low_rainfall:
        recommendations.append("Very low rainfall. Apply irrigation.")
    
    if high_rainfall:
        recommendations.append("Excess rainfall. Check for waterlogging.")

    # Check fertilizer application conditions
    optimum_temp = avg_temp >= 10 and avg_temp <= 29
    high_rainfall = avg_precip < 10
    
    if optimum_temp and high_rainfall:
        recommendations.append("Apply fertilizers")
    
    # Check harvesting conditions
    high_rainfall = avg_precip <= plant_min_precip
    low_humidity = avg_humidity <= threshold["humidity"]
    if high_rainfall and low_humidity:
        recommendations.append(f"Good conditions for harvesting {my_plant}.")
   
    return {
        "plant": my_plant,
        "plant_thresholds": threshold,
        "avg_temp": round(avg_temp, 1),
        "avg_precip": round(avg_precip, 1),
        "avg_humidity": round(avg_humidity, 1),
        "avg_solarradiation": round(avg_solar, 1),
        "recommendations": recommendations
    }

# endpoint: GET /plant_thresholds/<plant>
@app.route("/plant_thresholds/<plant>", methods=["GET"])
def get_plant_thresholds(plant: str):
    if plant.lower() not in PLANT_THRESHOLDS:
        return jsonify({"error": f"Unsupported plant {plant}"}), 400
    
    threshold = PLANT_THRESHOLDS[plant]
    return jsonify(threshold)

# endpoint: GET /recommendations/<month>?plant=tea
@app.route("/recommendations/<int:month>", methods=["GET"])
def get_monthly_recommendations(month):
    plant = request.args.get('plant', '').lower()

    if month < 1 or month > 12:
        return jsonify({"error": "Invalid month. Use 1-12."}), 400
    
    if plant not in PLANT_THRESHOLDS:
        return jsonify({"error": f"Unsupported plant {plant}"}), 400

    monthly_weather = weather[weather.index.month == month]
    if monthly_weather.empty:
        return jsonify({"error": "No data available for this month."}), 404

    result = get_recommendations(monthly_weather, plant)
    return jsonify(result)

# endpoint: GET /weather/today
@app.route("/weather/today", methods=["GET"])
def get_todays_weather():
    weather["month_day"] = weather.index.strftime("%m-%d")
    weather["year"] = weather.index.year

    today = datetime.now()
    month_day = today.strftime("%m-%d")

    # Filter the DataFrame for the matching day across all years
    data = weather[weather["month_day"] == month_day]

    forecast_columns = ["temp", "humidity", "precip", "conditions"]
    forecast = {}

    if not data.empty:
        forecast_date = datetime.strptime(f"2025-{month_day}", "%Y-%m-%d")
        forecast["date"] = forecast_date.isoformat()

        for col in forecast_columns:
            if col == "conditions":
                mode_values = data[col].mode()
                forecast[col] = mode_values.iloc[0] if not mode_values.empty else "Unknown"
            else:
                forecast[col] = round(data[col].mean(), 2)

    return jsonify(forecast)

# endpoint: GET /weather/<month>/<day>
@app.route("/weather/<int:month>/<int:day>", methods=["GET"])
def get_this_weeks_weather(month, day):
    # Extract month and day for grouping
    weather["month_day"] = weather.index.strftime("%m-%d")
    weather["year"] = weather.index.year

    # Define forecast target dates
    this_year = datetime.today().date().year
    today = datetime(this_year, month, day)
    upcoming_days = []

    for offset in range(1, 8):
        next_day = today + timedelta(days=offset)
        formatted_day = next_day.strftime("%m-%d")
        upcoming_days.append(formatted_day)

    forecast_columns = ["temp", "humidity", "precip", "conditions"]
    forecast = []

    # Calculate avg weather conditions over the years
    for month_day in upcoming_days:
        data = weather[weather["month_day"] == month_day]
        
        if not data.empty:
            avg = {
                "date": f"2025-{month_day}",
            }
            for col in forecast_columns:
                if col == "conditions":
                    # Most frequent condition
                    mode_values = data[col].mode()
                    if not mode_values.empty:
                        avg[col] = mode_values.iloc[0]
                    else:
                        avg[col] = "Unknown"
                else:
                    avg[col] = round(data[col].mean(), 2) 
            forecast.append(avg)

    forecast_df = pd.DataFrame(forecast)
    
    # Ensure 'date' column is datetime (in case it's a string)
    forecast_df['date'] = pd.to_datetime(forecast_df['date'])

    forecast_json = forecast_df.to_json(orient="records", date_format="iso")
    return forecast_json

# endpoint: GET /weather/<month>
@app.route("/weather/<int:month>", methods=["GET"])
def get_this_months_weather(month):
    if month < 1 or month > 12:
        return jsonify({"error": "Invalid month. Use 1-12."}), 400
    
    # Extract month-day and year from index
    weather["month_day"] = weather.index.strftime("%m-%d")
    weather["year"] = weather.index.year
    weather["month"] = weather.index.month
    weather["day"] = weather.index.day

    # Filter weather data for the requested month
    month_data = weather[weather["month"] == month]

    if month_data.empty:
        return jsonify({"error": "No weather data for this month"}), 404

    forecast_columns = ["tempmax", "tempmin", "temp", "humidity", "precip", "windspeed", "conditions"]
    forecast = []

    # Group by day of the month to aggregate per date
    grouped = month_data.groupby("day")

    for day, group in grouped:
        month_day_str = f"{month:02d}-{day:02d}"
        avg = {
            "date": f"2025-{month_day_str}",
        }
        for col in forecast_columns:
            if col == "conditions":
                # Most frequent conditions
                mode_values = group[col].mode()
                if not mode_values.empty:
                    avg[col] = mode_values.iloc[0]
                else:
                    avg[col] = "Unknown"
            else:
                avg[col] = round(group[col].mean(), 2)
        forecast.append(avg)

    forecast_df = pd.DataFrame(forecast)
    forecast_df['date'] = pd.to_datetime(forecast_df['date'], errors='coerce')
    forecast_df['day'] = forecast_df['date'].dt.day_name()

    forecast_json = forecast_df.to_json(orient="records", date_format="iso")
    return forecast_json

if __name__ == '__main__':
    app.run(debug=True)
