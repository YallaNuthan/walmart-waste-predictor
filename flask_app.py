from flask_cors import CORS
from flask import Flask, request, jsonify
import joblib
import numpy as np
import os
import pandas as pd
from datetime import datetime
import csv
from sklearn.linear_model import LinearRegression

app = Flask(__name__)
CORS(app)

# Load models and columns
model = joblib.load("waste_predictor_model.pkl")
model_columns = joblib.load("model_columns.pkl")
demand_model = joblib.load("demand_model.pkl")
ai_model = joblib.load("ai_score_model.pkl")

@app.route('/')
def home():
    return "Walmart Waste Predictor API is running!"

@app.route('/upload_csv', methods=['POST'])
def upload_csv():
    try:
        file = request.files['file']
        df = pd.read_csv(file)

        required_columns = {"product_id", "name", "category", "stock", "expiry_date", "store_location", "freshness_score"}
        if not required_columns.issubset(df.columns):
            return jsonify({"success": False, "error": "Missing required columns."})

        today = datetime.today().date()
        df["expiry_date"] = pd.to_datetime(df["expiry_date"], errors='coerce')
        df["days_to_expiry"] = df["expiry_date"].apply(
            lambda x: (x.date() - today).days if pd.notna(x) else pd.NA
        )

        def check_expiry_risk(row):
            if pd.isna(row["days_to_expiry"]) or pd.isna(row["freshness_score"]):
                return 0
            return 1 if row["days_to_expiry"] <= 2 and row["freshness_score"] < 0.7 else 0

        df["expiry_risk"] = df.apply(check_expiry_risk, axis=1)

        def label_expiry_status(days):
            if pd.isna(days):
                return "Invalid Date"
            elif days < 0:
                return "Already Expired"
            else:
                return f"{days} day(s) left"

        df["expiry_status"] = df["days_to_expiry"].apply(label_expiry_status)

        if 'previous_sales' not in df.columns:
            df['previous_sales'] = df['stock'].apply(lambda x: max(1, int(x * 0.7)))
        if 'temperature_C' not in df.columns:
            df['temperature_C'] = 25

        df["daily_demand"] = df.apply(
            lambda row: round(demand_model.predict([[row["previous_sales"], row["stock"], row["temperature_C"]]])[0], 2),
            axis=1
        )

        df["recommendation"] = df["expiry_risk"].apply(lambda r: "Donate" if r else "Keep in Stock")

        output = df[[
            "product_id", "name", "store_location", "category", "stock", "freshness_score",
            "expiry_status", "daily_demand", "expiry_risk", "recommendation"
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
        features = [json_['previous_sales'], json_['stock'], json_['temperature_C']]
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

        demand_features = [data['previous_sales'], data['stock'], data['temperature_C']]
        demand = demand_model.predict([demand_features])[0]

        action = "Donate" if expiry_risk == 1 and demand < 20 else \
                 "Transfer or Apply Discount" if expiry_risk == 1 else \
                 "Keep in Stock"

        return jsonify({
            'expiry_risk': int(expiry_risk),
            'forecasted_demand': round(demand, 2),
            'recommendation': action
        })
    except Exception as e:
        return jsonify({'error': str(e)})

@app.route("/bulk_recommendations", methods=["GET"])
def bulk_recommendations():
    try:
        inventory = pd.read_csv("data/product_inventory.csv", sep="\t")
        demand = pd.read_csv("data/store_demand.csv", sep="\t")
        distance = pd.read_csv("data/store_distance.csv", sep="\t")

        inventory["expiry_date"] = pd.to_datetime(inventory["expiry_date"], format="%d-%m-%Y", errors="coerce")
        today = datetime.today().date()
        inventory["days_to_expiry"] = inventory["expiry_date"].apply(
            lambda x: (x.date() - today).days if pd.notna(x) else pd.NA
        )

        def label_expiry_status(days):
            if pd.isna(days):
                return "Invalid Date"
            elif days < 0:
                return "Already Expired"
            else:
                return f"{days} day(s) left"

        inventory["expiry_status"] = inventory["days_to_expiry"].apply(label_expiry_status)
        inventory["expiry_date"] = inventory["expiry_date"].dt.strftime("%d-%m-%Y")

        merged = pd.merge(inventory, demand, on=["store_location", "product_id"], how="left")
        merged["expiry_risk"] = merged["days_to_expiry"].apply(
            lambda d: 1 if pd.notna(d) and d <= 1 else 0
        )

        def recommend_transfer(row):
            from_store = row["store_location"]
            product_id = row["product_id"]
            required_demand = row["daily_demand"]
            nearby = distance[distance["from_store"] == from_store]

            best_store = None
            min_distance = float("inf")
            for _, d in nearby.iterrows():
                to_store = d["to_store"]
                dist = d["distance_km"]
                match = demand[
                    (demand["store_location"] == to_store) &
                    (demand["product_id"] == product_id)
                ]
                if not match.empty and match.iloc[0]["daily_demand"] > required_demand and dist < min_distance:
                    best_store = to_store
                    min_distance = dist
            return best_store if best_store else "Keep in Stock"

        merged["recommendation"] = merged.apply(
            lambda row: "Donate" if row["expiry_risk"] else recommend_transfer(row),
            axis=1
        )

        return jsonify(merged[[
            "product_id", "name", "store_location", "category", "stock", "freshness_score",
            "expiry_date", "expiry_status", "daily_demand", "expiry_risk", "recommendation"
        ]].to_dict(orient="records"))
    except Exception as e:
        return jsonify({"error": str(e)})

# ==================== AI Leaderboard =========================
LEADERBOARD_FILE = "data/ai_leaderboard.csv"
if not os.path.exists(LEADERBOARD_FILE):
    pd.DataFrame(columns=[
        "store_location", "waste_donated_kg", "waste_reduced_kg",
        "waste_generated_kg", "date", "ai_score"
    ]).to_csv(LEADERBOARD_FILE, index=False)

@app.route("/upload_waste_ai", methods=["POST"])
def upload_waste_ai():
    try:
        file = request.files['file']
        df = pd.read_csv(file)

        required = {"store_location", "waste_donated_kg", "waste_reduced_kg", "waste_generated_kg", "date"}
        if not required.issubset(df.columns):
            return jsonify({"success": False, "error": "Missing required columns."})

        df["date"] = pd.to_datetime(df["date"], format="%d-%m-%Y", errors='coerce').dt.date

        X = df[["waste_donated_kg", "waste_reduced_kg", "waste_generated_kg"]]
        df["ai_score"] = ai_model.predict(X).round(2)

        df.to_csv(LEADERBOARD_FILE, mode="a", index=False, header=False)
        return jsonify({"success": True, "message": "Report uploaded with AI scores!"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route("/ai_daily_leaderboard", methods=["GET"])
def ai_daily_leaderboard():
    try:
        df = pd.read_csv(LEADERBOARD_FILE)
        df["date"] = pd.to_datetime(df["date"], errors='coerce').dt.date
        today = datetime.today().date()
        daily = df[df["date"] == today]
        daily = daily.sort_values("ai_score", ascending=False).reset_index(drop=True)
        daily["badge"] = ["🥇", "🥈", "🥉"] + [""] * (len(daily) - 3)
        daily["date"] = daily["date"].apply(lambda d: d.strftime("%d-%m-%Y") if pd.notna(d) else "")
        return jsonify(daily.to_dict(orient="records"))
    except Exception as e:
        return jsonify({"error": str(e)})

@app.route("/ai_monthly_leaderboard", methods=["GET"])
def ai_monthly_leaderboard():
    try:
        df = pd.read_csv(LEADERBOARD_FILE)
        df["date"] = pd.to_datetime(df["date"], errors='coerce').dt.date
        today = datetime.today()
        df = df[df["date"].apply(lambda d: d.month == today.month and d.year == today.year)]
        monthly = df.groupby("store_location").agg({
            "waste_donated_kg": "sum",
            "waste_reduced_kg": "sum",
            "waste_generated_kg": "sum",
            "ai_score": "mean"
        }).reset_index()
        monthly = monthly.sort_values("ai_score", ascending=False).reset_index(drop=True)
        monthly["badge"] = ["🏆"] + [""] * (len(monthly) - 1)
        return jsonify(monthly.to_dict(orient="records"))
    except Exception as e:
        return jsonify({"error": str(e)})

# Run the Flask app
if __name__ == '__main__':
    print("✅ Starting Flask...")
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
