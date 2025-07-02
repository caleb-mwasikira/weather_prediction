from flask import Flask, jsonify, request
import pandas as pd

app = Flask(__name__)

PLANT_THRESHOLDS = {
    "tea": {
        "min_temp": 15,
        "max_temp": 25,
        "min_rainfall": 12,
        "max_rainfall": 15,
        "humidity": 60,
    },
    "coffee/arabica": {
        "min_temp": 18,
        "max_temp": 24,
        "min_rainfall": 15,
        "max_rainfall": 20,
        "humidity": 50,
        "altitude": (100, 800),
    },
    "coffee/robusta": {
        "min_temp": 24,
        "max_temp": 30,
        "min_rainfall": 20,
        "max_rainfall": 30,
        "humidity": 50,
        "altitude": (180, 760),
    }
}

def load_weather_data() -> pd.DataFrame:
    print("Loading weather data...\n")
    weather_2020 = pd.read_csv("./weather_data/Kericho, Kenya 2020-01-01 to 2020-12-31.csv", index_col="datetime")
    weather_2021 = pd.read_csv("./weather_data/Kericho, Kenya 2021-01-01 to 2021-12-31.csv", index_col="datetime")
    weather_2022 = pd.read_csv("./weather_data/Kericho, Kenya 2022-01-01 to 2022-12-31.csv", index_col="datetime")
    weather_2023 = pd.read_csv("./weather_data/Kericho, Kenya 2023-01-01 to 2023-12-31.csv", index_col="datetime")
    weather_2024 = pd.read_csv("./weather_data/Kericho, Kenya 2024-01-01 to 2024-12-31.csv", index_col="datetime")

    weather = pd.concat([weather_2020,weather_2021,weather_2022,weather_2023,weather_2024], axis=0)
    weather.index = pd.to_datetime(weather.index)
    return weather

weather = load_weather_data()

def get_recommendations(weather, my_plant):
    if my_plant not in PLANT_THRESHOLDS.keys():
        return {"error": f"Unsupported plant {my_plant}"}

    threshold = PLANT_THRESHOLDS[my_plant]
    actions = {
        "planting": [],
        "irrigation": [],
        "fertilization": [],
        "harvesting": []
    }

    avg_temp = weather['temp'].mean()
    avg_precip = weather['precip'].mean()
    avg_humidity = weather['humidity'].mean()
    avg_solar = weather['solarradiation'].mean()
    
    plant_min_temp = threshold["min_temp"]
    plant_min_rainfall = threshold["min_rainfall"] 
    plant_max_rainfall = threshold["max_rainfall"]
    
    optimum_temp = (avg_temp / plant_min_temp) >= 0.6
    high_rainfall = (avg_precip / plant_min_rainfall) >= 0.6

    # Check planting conditions
    if optimum_temp and high_rainfall:
        actions["planting"].append(f"Good conditions to plant {my_plant}.")
    
    # Check irrigation conditions
    low_rainfall = (avg_precip / plant_min_rainfall) < 0.5
    high_rainfall = (avg_precip / plant_max_rainfall) > 0.5
    if low_rainfall:
        actions["irrigation"].append("Very low rainfall. Apply irrigation.")
    
    if high_rainfall:
        actions["irrigation"].append("Excess rainfall. Check for waterlogging.")

    # Check fertilizer application conditions
    optimum_temp = avg_temp >= 10 and avg_temp <= 29
    high_rainfall = avg_precip < 10
    
    if optimum_temp and high_rainfall:
        actions["fertilization"].append("Apply fertilizers")
    
    # Check harvesting conditions
    high_rainfall = avg_precip <= plant_min_rainfall
    low_humidity = avg_humidity <= threshold["humidity"]
    if high_rainfall and low_humidity:
        actions["harvesting"].append(f"Good conditions for harvesting {my_plant}.")
   
    return {
        "plant": my_plant,
        "plant_thresholds": threshold,
        "avg_temp": round(avg_temp, 1),
        "avg_precip": round(avg_precip, 1),
        "avg_humidity": round(avg_humidity, 1),
        "avg_solarradiation": round(avg_solar, 1),
        "recommendations": actions
    }

# endpoint: GET /plant_thresholds/<plant>
@app.route("/plant_thresholds/<plant>", methods=["GET"])
def get_plant_thresholds(plant):
    if plant not in PLANT_THRESHOLDS.keys():
        return jsonify({"error": f"Unsupported plant {plant}"}), 400
    
    threshold = PLANT_THRESHOLDS[plant]
    return jsonify(threshold)

# endpoint: GET /recommendations/<month>?plant=tea
@app.route("/recommendations/<int:month>", methods=["GET"])
def get_monthly_recommendations(month):
    plant = request.args.get('plant', '').lower()

    if month < 1 or month > 12:
        return jsonify({"error": "Invalid month. Use 1-12."}), 400
    
    if plant not in PLANT_THRESHOLDS.keys():
        return jsonify({"error": f"Unsupported plant {plant}"}), 400

    monthly_weather = weather[weather.index.month == month]
    if monthly_weather.empty:
        return jsonify({"error": "No data available for this month."}), 404

    result = get_recommendations(monthly_weather, plant)
    return jsonify(result)

# endpoint: GET /recommendations/week/<week>?plant=tea
@app.route("/recommendations/week/<int:week>", methods=["GET"])
def get_weekly_recommendations(week):
    plant = request.args.get('plant', '').lower()

    if week < 1 or week > 53: # 1-53 Number of weeks in a year
        return jsonify({"error": "Invalid week. Use 1-53."}), 400

    if plant not in PLANT_THRESHOLDS:
        return jsonify({"error": f"Unsupported plant {plant}"}), 400

    weekly_weather = weather[weather.index.isocalendar().week == week]
    if weekly_weather.empty:
        return jsonify({"error": f"No weather data for week {week}."}), 404

    result = get_recommendations(weekly_weather, plant)
    return jsonify(result)


# endpoint: GET /recommendations/<month>/<week>?plant=tea
@app.route("/recommendations/<int:month>/<int:week>", methods=["GET"])
def get_week_of_month_recommendations(month, week):
    plant = request.args.get('plant', '').lower()

    if month < 1 or month > 12:
        return jsonify({"error": "Invalid month. Use 1-12."}), 400
    if week < 1 or week > 5:
        return jsonify({"error": "Invalid week of month. Use 1-5."}), 400
    if plant not in PLANT_THRESHOLDS:
        return jsonify({"error": f"Unsupported plant {plant}"}), 400

    if not isinstance(weather.index, pd.DatetimeIndex):
        return jsonify({"error": "Weather index is not datetime."}), 500

    def get_week_of_month(date):
        first_day = date.replace(day=1)
        return ((date.day + first_day.weekday()) // 7) + 1

    weather2 = weather.copy()
    weather2["month"] = weather2.index.month
    weather2["week_of_month"] = weather2.index.to_series().apply(get_week_of_month)

    filtered_weather = weather2[
        (weather2["month"] == month) &
        (weather2["week_of_month"] == week)
    ]

    if filtered_weather.empty:
        return jsonify({"error": f"No weather data for month {month}, week {week}."}), 404

    result = get_recommendations(filtered_weather, plant)
    return jsonify(result)


if __name__ == '__main__':
    app.run(debug=True)
