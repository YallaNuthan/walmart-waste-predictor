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

@app.route('/upload_csv', methods=['POST'])
def upload_csv():
    try:
        file = request.files['file']
        df = pd.read_csv(file)

        # Validate required columns
        required_columns = {"product_id", "name", "category", "stock", "expiry_date", "store_location", "freshness_score"}
        if not required_columns.issubset(df.columns):
            return jsonify({"success": False, "error": "Missing one or more required columns."})

        # Convert expiry_date and calculate days_to_expiry
        today = datetime.today().date()
        df["expiry_date"] = pd.to_datetime(df["expiry_date"], errors='coerce')
        df["days_to_expiry"] = (df["expiry_date"].dt.date - today).dt.days

        # Simple expiry risk logic
        df["expiry_risk"] = df.apply(
            lambda row: 1 if row["days_to_expiry"] <= 2 and row["freshness_score"] < 0.7 else 0,
            axis=1
        )

        # Simple recommendation logic
        df["recommendation"] = df["expiry_risk"].apply(lambda r: "Donate" if r else "Keep in Stock")

        # Return filtered response
        output = df[[
            "product_id", "name", "store_location", "category", "stock", "freshness_score",
            "days_to_expiry", "expiry_risk", "recommendation"
        ]].to_dict(orient="records")

        return jsonify({"success": True, "data": output})

    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route('/predict', methods=['POST'])
def predict():
    try:
        json_ = request.json
        query = [json_[col] for col in model_columns]
        prediction = model.predict([query])[0]
        label = "High Risk" if prediction == 1 else "Low Risk"
        return jsonify({'prediction': label})

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
    inventory = pd.read_csv("data/product_inventory.csv", sep="\t")
    demand = pd.read_csv("data/store_demand.csv", sep='\t')
    distance = pd.read_csv("data/store_distance.csv", sep='\t')

    def safe_parse_date(x):
        try:
            return datetime.strptime(x, "%d-%m-%Y")
        except:
            return pd.NaT

    inventory["expiry_date"] = inventory["expiry_date"].astype(str).apply(safe_parse_date)

# Step 4: Calculate days_to_expiry
    today = datetime.today().date()
    inventory["days_to_expiry"] = (inventory["expiry_date"].dt.date - today).apply(lambda x: x.days if pd.notna(x) else pd.NA)


# Step 5: Label status
    def label_expiry_status(days):
        if pd.isna(days):
            return "Invalid Date"
        elif days < 0:
            return "Already Expired"
        else:
            return f"{days} day(s) left"

    inventory["expiry_status"] = inventory["days_to_expiry"].apply(label_expiry_status)

# Step 6 (optional): Format expiry_date for table display
    inventory["expiry_date"] = inventory["expiry_date"].dt.strftime("%d-%m-%Y")

  


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

    # Add expiry_status column first
    merged["expiry_status"] = merged["days_to_expiry"].apply(
        lambda d: "Already Expired" if d < 0 else f"{d} day(s)"
    )

# Format expiry_date (optional but nice)
    merged["expiry_date"] = merged["expiry_date"].dt.strftime("%d-%m-%Y")

# Then return this
    return merged[[
        "product_id", "name", "store_location", "category", "stock", "freshness_score",
        "expiry_date", "expiry_status", "daily_demand", "expiry_risk", "recommendation"
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
