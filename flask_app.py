from flask_cors import CORS
from flask import Flask, request, jsonify
import joblib
import numpy as np
import os
import pandas as pd
from datetime import datetime

app = Flask(__name__)
CORS(app)

# Load models and columns
model = joblib.load("waste_predictor_model.pkl")
model_columns = joblib.load("model_columns.pkl")
demand_model = joblib.load("demand_model.pkl")

@app.route('/')
def home():
    return "Walmart Waste Predictor API is running!"

@app.route('/predict', methods=['POST'])
def predict():
    try:
        json_ = request.json
        query = [json_[col] for col in model_columns]
        prediction = model.predict([query])[0]
        return jsonify({'prediction': int(prediction)})
    except Exception as e:
        return jsonify({'error': str(e)})

@app.route('/forecast_demand', methods=['POST'])
def forecast_demand():
    try:
        json_ = request.json
        features = [
            json_['previous_sales'],
            json_['stock'],
            json_['temperature_C']
        ]
        prediction = demand_model.predict([features])[0]
        return jsonify({'forecasted_demand': round(prediction, 2)})
    except Exception as e:
        return jsonify({'error': str(e)})

@app.route('/recommend_action', methods=['POST'])
def recommend_action():
    try:
        data = request.json
        expiry_features = [data[col] for col in model_columns]
        expiry_risk = model.predict([expiry_features])[0]

        demand_features = [
            data['previous_sales'],
            data['stock'],
            data['temperature_C']
        ]
        demand = demand_model.predict([demand_features])[0]

        if expiry_risk == 1:
            action = "Donate" if demand < 20 else "Transfer or Apply Discount"
        else:
            action = "Keep in Stock"

        return jsonify({
            'expiry_risk': int(expiry_risk),
            'forecasted_demand': round(demand, 2),
            'recommendation': action
        })
    except Exception as e:
        return jsonify({'error': str(e)})

# ✅ Real data processing logic
def generate_recommendations():
    inventory = pd.read_csv("data/product_inventory.csv")
    demand = pd.read_csv("data/store_demand.csv")
    distance = pd.read_csv("data/store_distance.csv")

    # Use ISO format "%Y-%m-%d" if CSV has "2025-07-04" style dates
    inventory["expiry_date"] = pd.to_datetime(inventory["expiry_date"], format="%Y-%m-%d")
    today = datetime.strptime("2025-06-30", "%Y-%m-%d")
    inventory["days_to_expiry"] = (inventory["expiry_date"] - today).dt.days

    merged = pd.merge(inventory, demand, how='left', on=["product_id", "store_location"])

    def classify_risk(row):
        return 1 if row["days_to_expiry"] <= 2 and row["freshness_score"] < 0.7 else 0

    merged["expiry_risk"] = merged.apply(classify_risk, axis=1)

    def recommend_transfer(row):
        from_store = row["store_location"]
        product_id = row["product_id"]
        required_demand = row["daily_demand"]

        options = distance[distance["from_store"] == from_store]
        best_store = None
        min_distance = float("inf")

        for _, d in options.iterrows():
            to_store = d["to_store"]
            dist = d["distance_km"]
            match = demand[(demand["store_location"] == to_store) & (demand["product_id"] == product_id)]
            if not match.empty and match.iloc[0]["daily_demand"] > required_demand and dist < min_distance:
                best_store = to_store
                min_distance = dist

        return best_store if best_store else "Keep in Stock"

    merged["recommendation"] = merged.apply(
        lambda row: "Donate" if row["expiry_risk"] else recommend_transfer(row),
        axis=1
    )

    return merged[[
        "product_id", "name", "store_location", "category", "stock", "freshness_score",
        "days_to_expiry", "daily_demand", "expiry_risk", "recommendation"
    ]].to_dict(orient="records")

# ✅ Register the smart recommendation route
@app.route("/bulk_recommendations", methods=["GET"])
def bulk_recommendations():
    data = generate_recommendations()
    return jsonify(data)

# ✅ Run Flask server
if __name__ == '__main__':
    print("✅ Starting Flask...")
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
