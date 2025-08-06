from flask import Flask, jsonify, request
import pandas as pd
from datetime import datetime, timedelta
from data_prep import load_weather_data, CROP_THRESHOLDS

app = Flask(__name__)

weather = load_weather_data("weather_data")

def get_recommendations(weather_data, crop):
    """
    Generates agricultural recommendations based on weather data for a given crop.

    Args:
        weather_data (pd.DataFrame): Weather data (temp, precip, humidity, solarradiation)
                                                for the specified period. This will now typically be
                                                a wider rolling window (e.g., 21 days).
        crop (str): The name of the crop for which to get recommendations (e.g., "corn", "wheat").

    Returns:
        dict: A dictionary containing recommendations or an error message.
    """
    if crop not in CROP_THRESHOLDS:
        return {"error": f"Unsupported crop '{crop}'"}

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

    threshold = CROP_THRESHOLDS[crop]
    max_temp = threshold["max_temp"]
    min_precip = threshold["min_precip"]
    max_precip = threshold["max_precip"]
    max_humidity = threshold["max_humidity"]

    recommendations = []
    recent_precip = weather_data['precip'].iloc[-1] if not weather_data['precip'].empty else 0
    is_currently_raining = recent_precip > 0.5

    # Planting Conditions Recommendations
    if avg_precip > max_precip:
        recommendations.append(f"High avg rain. Good conditions for planting {crop}.")
    
    # Check for ideal planting conditions
    elif avg_temp >= max_temp and min_precip <= avg_precip <= max_precip:
        recommendations.append(f"Good conditions for planting {crop}.")
    
    # Check for temperature too low
    elif avg_temp < max_temp:
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
        recommendations.append(f"Good for harvesting {crop}.")

    if not recommendations:
        recommendations.append("No specific recommendations for current conditions.")

    return recommendations

ROLLING_WINDOW_DAYS = 21

@app.route("/recommendations/<string:location>/<int:month>/<int:day>", methods=["GET"])
def get_weekly_recommendations(location, month, day):
    """
    Provides agricultural recommendations for a specific week, using a rolling window
    of weather data to provide steadier advice.

    Args:
        location (string): Area of interest.
        month (int): The month of the desired week.
        day (int): The day of the desired week.

    Query Parameters:
        crop (str): The name of the crop (e.g., "corn", "wheat").

    Returns:
        JSON: A JSON response containing crop, week details, and recommendations.
    """
    crop = request.args.get('crop', '').lower()

    if crop not in CROP_THRESHOLDS:
        return jsonify({"error": f"Unsupported crop '{crop}'"}), 400

    # Filter weather data based on a location
    local_weather = weather[weather["name"] == location]
    if local_weather.empty:
        return jsonify({"error": f"No weather data found for location {location}"})

    try:
        year = local_weather.index[0].year
        query_date = datetime(year, month, day)
    except ValueError:
        return jsonify({"error": "Invalid date."}), 400

    week_end_for_query = query_date + timedelta(days=(6 - query_date.weekday()))
    rolling_window_start = week_end_for_query - timedelta(days=ROLLING_WINDOW_DAYS - 1)

    # Filter local_weather data for this calculated rolling window
    rolling_weather = local_weather[
        (local_weather.index.date >= rolling_window_start.date()) &
        (local_weather.index.date <= week_end_for_query.date())
    ]

    if rolling_weather.empty:
        return jsonify({"error": "No weather data available for the specified rolling period."}), 404

    recommendations = get_recommendations(rolling_weather, crop)

    return jsonify({
        "crop": crop,
        "week_start": (query_date - timedelta(days=query_date.weekday())).strftime("%Y-%m-%d"),
        "week_end": week_end_for_query.strftime("%Y-%m-%d"),
        "recommendations": recommendations
    })

def is_suitable_crop(weather_data, crop_thresholds):
    """
    Checks whether a crop is suitable to grow in certain weather conditions.
    Returns True if 75% or more parameters are met.
    """
    # Evaluate each season for crop suitability
    suitable_seasons = []

    for _, row in weather_data.iterrows():
        score = 0
        total = 4  # number of parameters being checked

        season_temp = row["temp"]
        season_precip = row["precip"]
        season_humidity = row["humidity"]
        season_solarradiation = row["solarradiation"]

        if crop_thresholds["min_temp"] <= season_temp <= crop_thresholds["max_temp"]:
            score += 1
        if crop_thresholds["min_precip"] <= season_precip <= crop_thresholds["max_precip"]:
            score += 1
        if crop_thresholds["min_humidity"] <= season_humidity <= crop_thresholds["max_humidity"]:
            score += 1
        if crop_thresholds["min_solarradiation"] <= season_solarradiation <= crop_thresholds["max_solarradiation"]:
            score += 1

        if score / total >= 0.75:
            suitable_seasons.append({
                "year": int(row["year"]),
                "season": row["season"],
                "score": score / total,
                "avg_temp": round(row["temp"], 1),
                "total_rain": round(row["precip"], 1),
                "avg_humidity": round(row["humidity"], 1),
                "avg_solarradiation": round(row["solarradiation"], 1)
            })

    return len(suitable_seasons) > 0

# endpoint: GET /all-crops
@app.route("/all-crops", methods=["GET"])
def get_all_crops():
    crops: list[dict[str, dict]] = []
    
    for crop, threshold in CROP_THRESHOLDS.items():
        threshold["name"] = crop
        crops.append(threshold)
    
    return jsonify(crops)

# endpoint: GET /all-locations
@app.route("/all-locations", methods=["GET"])
def get_all_locations():
    locations = weather["name"].unique().tolist()
    return jsonify(locations)

# endpoint: GET /crop_thresholds/<crop>
@app.route("/crop_thresholds/<string:crop>", methods=["GET"])
def get_crop_thresholds(crop):
    crop = crop.lower()
    if crop not in CROP_THRESHOLDS:
        return jsonify({"error": f"Unsupported crop {crop}"}), 400
    
    threshold = CROP_THRESHOLDS[crop]
    threshold["name"] = crop
    
    return jsonify(threshold)

# endpoint: GET /suitable_crops/<location>
@app.route("/suitable_crops/<string:location>", methods=["GET"])
def get_suitable_crops(location):
    # Filter weather data based on a location
    local_weather = weather[weather["name"] == location]
    if local_weather.empty:
        return jsonify({"error": f"No weather data found for location {location}"})

    suitable_crops: list[dict[str, dict]] = []

    for crop, threshold in CROP_THRESHOLDS.items():
        if is_suitable_crop(local_weather, threshold):
            threshold["name"] = crop
            suitable_crops.append(threshold)
        else:
            print(f"Crop {crop} not suitable to grow in {location}")

    if not suitable_crops:
        return jsonify({"error": f"No crops suitable to grow in {location} were found"})

    return jsonify(suitable_crops)

# endpoint: GET /weather/today
@app.route("/weather/today/<string:location>", methods=["GET"])
def get_todays_weather(location):
    # Filter weather data based on a location
    local_weather = weather[weather["name"] == location]
    if local_weather.empty:
        return jsonify({"error": f"No weather data found for location {location}"})

    local_weather["month_day"] = local_weather.index.strftime("%m-%d")
    local_weather["year"] = local_weather.index.year

    today = datetime.now()
    month_day = today.strftime("%m-%d")

    # Filter the DataFrame for the matching day across all years
    data = local_weather[local_weather["month_day"] == month_day]

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
@app.route("/weather/<string:location>/<int:month>/<int:day>", methods=["GET"])
def get_this_weeks_weather(location, month, day):
    # Filter weather data based on a location
    local_weather = weather[weather["name"] == location]
    if local_weather.empty:
        return jsonify({"error": f"No weather data found for location {location}"})

    local_weather.loc[:, "month_day"] = local_weather.index.strftime("%m-%d")
    local_weather.loc[:, "year"] = local_weather.index.year

    # Define forecast target dates
    this_year = datetime.today().date().year
    today = datetime(this_year, month, day)
    upcoming_days = []

    for offset in range(1, 8):
        next_day = today + timedelta(days=offset)
        formatted_day = next_day.strftime("%m-%d")
        upcoming_days.append(formatted_day)

    forecast_columns = ["tempmax", "tempmin", "temp", "humidity", "precip", "windspeed", "conditions"]
    forecast = []

    # Calculate avg local_weather conditions over the years
    for month_day in upcoming_days:
        data = local_weather[local_weather["month_day"] == month_day]
        
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
@app.route("/weather/<string:location>/<int:month>", methods=["GET"])
def get_this_months_weather(location, month):
    if month < 1 or month > 12:
        return jsonify({"error": "Invalid month. Use 1-12."}), 400
    
    # Filter weather data based on a location
    local_weather = weather[weather["name"] == location]
    if local_weather.empty:
        return jsonify({"error": f"No weather data found for location {location}"})
    
    # Extract month-day and year from index
    local_weather["month_day"] = local_weather.index.strftime("%m-%d")
    local_weather["year"] = local_weather.index.year
    local_weather["month"] = local_weather.index.month
    local_weather["day"] = local_weather.index.day

    month_data = local_weather[local_weather["month"] == month]

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
