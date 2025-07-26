from flask import Flask, jsonify, request
import pandas as pd
from datetime import datetime, timedelta

from data_prep import load_weather_data

app = Flask(__name__)

PLANT_THRESHOLDS: dict[str, dict] = {
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

weather = load_weather_data()

def get_recommendations(weather_data, my_plant):
    """
    Generates agricultural recommendations based on weather data for a given plant.

    Args:
        weather_data (pd.DataFrame): Weather data (temp, precip, humidity, solarradiation)
                                                for the specified period. This will now typically be
                                                a wider rolling window (e.g., 21 days).
        my_plant (str): The name of the plant for which to get recommendations (e.g., "corn", "wheat").

    Returns:
        dict: A dictionary containing recommendations or an error message.
    """
    if my_plant not in PLANT_THRESHOLDS:
        return {"error": f"Unsupported plant '{my_plant}'"}

    if not isinstance(weather_data, pd.DataFrame):
        try:
            weather_data = pd.DataFrame(weather_data)
        except Exception as e:
            return {"error": f"Invalid weather data format: {e}"}

    required_cols = ['temp', 'precip', 'humidity', 'solarradiation']
    if not all(col in weather_data.columns for col in required_cols):
        return {"error": f"Missing required weather data columns. Need: {', '.join(required_cols)}"}

    avg_temp = weather_data['temp'].mean()
    avg_precip = weather_data['precip'].mean()
    avg_humidity = weather_data['humidity'].mean()
    avg_solar = weather_data['solarradiation'].mean()

    threshold = PLANT_THRESHOLDS[my_plant]
    min_temp = threshold["min_temp"]
    min_precip = threshold["min_precip"]
    max_precip = threshold["max_precip"]
    max_humidity = threshold["humidity"]

    recommendations = []

    recent_precip = weather_data['precip'].iloc[-1] if not weather_data['precip'].empty else 0
    
    is_currently_raining = recent_precip > 0.5

    # Planting Conditions Recommendations
    if avg_precip > max_precip:
        recommendations.append(f"High avg rain. Good conditions for planting {my_plant}.")
    
    # Check for ideal planting conditions
    elif avg_temp >= min_temp and min_precip <= avg_precip <= max_precip:
        recommendations.append(f"Good conditions for planting {my_plant}.")
    
    # Check for temperature too low
    elif avg_temp < min_temp:
        recommendations.append(f"Temp too low. Wait for warmer conditions.")
    
    # Check for rainfall too low, with a nuance for current rain
    elif avg_precip < min_precip:
        if is_currently_raining:
            recommendations.append(f"Avg rain low, but currently raining. Monitor closely.")
        else:
            recommendations.append(f"Rainfall too low. Irrigation may be needed.")

    # Irrigation Recommendations
    # Suggest irrigation if average is very low AND it's not currently raining significantly
    if avg_precip < (0.5 * min_precip) and not is_currently_raining:
        recommendations.append(f"Very low avg rain. Apply irrigation.")
    
    elif avg_precip < (0.5 * min_precip) and is_currently_raining:
         recommendations.append(f"Very low avg rain, but currently raining. Monitor water levels.")

    # Waterlogging Warning
    if avg_precip > max_precip * 1.2:
        recommendations.append(f"Excessive avg rain. High waterlogging risk. Ensure drainage.")
    
    # Flag potential waterlogging if recent rain is high, even if average isn't extremely high
    elif recent_precip > max_precip * 0.5:
         recommendations.append(f"High recent rain. Potential waterlogging risk. Monitor.")

    # Favorable conditions for fertilizer application, avoiding waterlogged soil and active rain
    if 10 <= avg_temp <= 29 and avg_precip < 10 and not is_currently_raining and recent_precip < 5:
        recommendations.append("Favorable for fertilizer application.")
    
    # If conditions are otherwise favorable but it's currently raining
    elif 10 <= avg_temp <= 29 and avg_precip < 10 and is_currently_raining:
        recommendations.append("Favorable for fertilizer, but currently raining. Apply after rain subsides.")

    # Harvesting Conditions Recommendations
    if avg_precip <= min_precip and avg_humidity <= max_humidity:
        recommendations.append(f"Good for harvesting {my_plant}.")

    if not recommendations:
        recommendations.append("No specific recommendations for current conditions.")

    return recommendations

ROLLING_WINDOW_DAYS = 21

@app.route("/recommendations/<int:month>/<int:day>", methods=["GET"])
def get_weekly_recommendations(month, day):
    """
    Provides agricultural recommendations for a specific week, using a rolling window
    of weather data to provide steadier advice.

    Args:
        month (int): The month of the desired week.
        day (int): The day of the desired week.

    Query Parameters:
        plant (str): The name of the plant (e.g., "corn", "wheat").

    Returns:
        JSON: A JSON response containing plant, week details, and recommendations.
    """
    plant = request.args.get('plant', '').lower()

    if plant not in PLANT_THRESHOLDS:
        return jsonify({"error": f"Unsupported plant '{plant}'"}), 400

    try:
        year = weather.index[0].year
        query_date = datetime(year, month, day)
    except ValueError:
        return jsonify({"error": "Invalid date."}), 400

    week_end_for_query = query_date + timedelta(days=(6 - query_date.weekday()))
    rolling_window_start = week_end_for_query - timedelta(days=ROLLING_WINDOW_DAYS - 1)

    # Filter weather data for this calculated rolling window
    rolling_weather = weather[
        (weather.index.date >= rolling_window_start.date()) &
        (weather.index.date <= week_end_for_query.date())
    ]

    if rolling_weather.empty:
        return jsonify({"error": "No weather data available for the specified rolling period."}), 404

    recommendations = get_recommendations(rolling_weather, plant)

    return jsonify({
        "plant": plant,
        "week_start": (query_date - timedelta(days=query_date.weekday())).strftime("%Y-%m-%d"),
        "week_end": week_end_for_query.strftime("%Y-%m-%d"),
        "recommendations": recommendations
    })

# endpoint: GET /plant_thresholds/<plant>
@app.route("/plant_thresholds/<plant>", methods=["GET"])
def get_plant_thresholds(plant):
    plant = plant.lower()
    if plant not in PLANT_THRESHOLDS:
        return jsonify({"error": f"Unsupported plant {plant}"}), 400
    
    threshold = PLANT_THRESHOLDS[plant]
    return jsonify(threshold)

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
