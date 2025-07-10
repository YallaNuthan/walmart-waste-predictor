from flask_cors import CORS
from flask import Flask, request, jsonify
import joblib
import numpy as np
import os
import pandas as pd
from datetime import datetime
from prophet import Prophet

app = Flask(__name__)
CORS(app)

# Load Models
model = joblib.load("waste_predictor_model.pkl")
model_columns = joblib.load("model_columns.pkl")
demand_model = joblib.load("demand_model.pkl")
ai_model = joblib.load("ai_score_model.pkl")

@app.route('/')
def home():
    return "Walmart Waste Predictor API is running!"

# === SMART BULK RECOMMENDATIONS ===
last_recommendation_df = pd.DataFrame()

@app.route('/upload_csv', methods=['POST'])
def upload_csv():
    global last_recommendation_df
    try:
        file = request.files['file']
        df = pd.read_csv(file)

        required_columns = {"product_id", "name", "category", "stock", "expiry_date", "store_location", "freshness_score"}
        if not required_columns.issubset(df.columns):
            return jsonify({"success": False, "error": "Missing required columns."})

        today = datetime.today().date()
        df["expiry_date"] = pd.to_datetime(df["expiry_date"], errors='coerce')
        df["days_to_expiry"] = df["expiry_date"].apply(lambda x: (x.date() - today).days if pd.notna(x) else pd.NA)

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

        recommendations = df[[
            "product_id", "name", "store_location", "category", "stock", "freshness_score",
            "expiry_status", "daily_demand", "expiry_risk", "recommendation"
        ]].to_dict(orient="records")

        # Save last dataframe for chart use
        last_recommendation_df = df.copy()

        alerts_df = df[
            (df["days_to_expiry"] < 1) |
            ((df["stock"] > 50) & (df["daily_demand"] < 10)) |
            ((df["daily_demand"] > 80) & (df["stock"] < 20) & (df["days_to_expiry"] > 1))
        ].copy()

        def detect_reason(row):
            if row["days_to_expiry"] < 1:
                return "❗ Expiring Today"
            elif row["stock"] > 50 and row["daily_demand"] < 10:
                return "📉 Overstocked, Low Demand"
            elif row["daily_demand"] > 80 and row["stock"] < 20:
                return "⚡ Demand Surge, Low Stock"
            return "Unknown"

        alerts_df["alert_reason"] = alerts_df.apply(detect_reason, axis=1)
        alerts_df["expiry_date"] = alerts_df["expiry_date"].dt.strftime("%d-%m-%Y")

        alerts = alerts_df[[
            "product_id", "name", "store_location", "category", "stock",
            "expiry_date", "daily_demand", "days_to_expiry", "alert_reason"
        ]].to_dict(orient="records")

        return jsonify({"success": True, "recommendations": recommendations, "alerts": alerts})

    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route('/chart_smart_bulk', methods=['GET'])
def chart_smart_bulk():
    try:
        global last_recommendation_df
        if last_recommendation_df.empty:
            return jsonify({"error": "No smart bulk data uploaded yet."}), 400

        grouped = last_recommendation_df.groupby("category")["stock"].sum().reset_index()
        return jsonify({
            "labels": grouped["category"].tolist(),
            "data": grouped["stock"].tolist()
        })
    except Exception as e:
        return jsonify({"error": str(e)})

# === RISK PREDICTOR ===
@app.route('/predict', methods=['POST'])
def predict():
    try:
        json_ = request.json
        query = [json_[col] for col in model_columns]
        prediction = model.predict([query])[0]
        return jsonify({'prediction': "High Risk" if prediction else "Low Risk"})
    except Exception as e:
        return jsonify({'error': str(e)})

# === DEMAND FORECAST ===
@app.route('/forecast_demand', methods=['POST'])
def forecast_demand():
    try:
        json_ = request.json
        features = [json_['previous_sales'], json_['stock'], json_['temperature_C']]
        prediction = demand_model.predict([features])[0]
        return jsonify({'forecasted_demand': round(prediction, 2)})
    except Exception as e:
        return jsonify({'error': str(e)})

# === WASTE FORECAST ===
@app.route("/forecast_waste", methods=["POST"])
def forecast_waste():
    try:
        file = request.files.get('file')
        if not file:
            return jsonify({"error": "No file uploaded"}), 400

        df = pd.read_csv(file)
        expected_columns = {"store_location", "item_name", "date", "waste_kg"}
        if not expected_columns.issubset(df.columns):
            return jsonify({"error": f"Missing required columns: {expected_columns}"}), 400

        df["date"] = pd.to_datetime(df["date"], format="%d-%m-%Y", errors="coerce")
        df = df.dropna(subset=["date", "waste_kg"])
        df["waste_kg"] = pd.to_numeric(df["waste_kg"], errors="coerce")

        results = []
        grouped = df.groupby(["store_location", "item_name"])
        for (store, item), group_df in grouped:
            group_df = group_df.rename(columns={"date": "ds", "waste_kg": "y"}).sort_values("ds")
            if len(group_df) < 2:
                continue
            model = Prophet()
            model.fit(group_df[["ds", "y"]])
            forecast = model.predict(model.make_future_dataframe(periods=7))
            forecast_result = forecast[["ds", "yhat"]].tail(7)
            forecast_result["ds"] = forecast_result["ds"].dt.strftime("%d-%m-%Y")
            for _, row in forecast_result.iterrows():
                results.append({
                    "store_location": store,
                    "item_name": item,
                    "date": row["ds"],
                    "predicted_waste_kg": round(row["yhat"], 2)
                })

        return jsonify(results)

    except Exception as e:
        return jsonify({"error": str(e)})

# === AI LEADERBOARD SYSTEM ===
LEADERBOARD_FILE = "data/ai_leaderboard.csv"
if not os.path.exists(LEADERBOARD_FILE):
    os.makedirs("data", exist_ok=True)
    pd.DataFrame(columns=[
        "store_location", "waste_donated_kg", "waste_reduced_kg", "waste_generated_kg", "date", "ai_score"
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
        df["ai_score"] = ai_model.predict(df[["waste_donated_kg", "waste_reduced_kg", "waste_generated_kg"]]).round(2)
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
        daily = daily.drop_duplicates("store_location").sort_values("ai_score", ascending=False).reset_index(drop=True)
        daily["badge"] = ["🥇", "🥈", "🥉"] + [""] * (len(daily) - 3)
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
        }).reset_index().sort_values("ai_score", ascending=False)
        monthly["badge"] = ["🏆"] + [""] * (len(monthly) - 1)
        return jsonify(monthly.to_dict(orient="records"))
    except Exception as e:
        return jsonify({"error": str(e)})

@app.route("/ai_leaderboard_by_date", methods=["GET"])
def ai_leaderboard_by_date():
    try:
        date_str = request.args.get("date")
        if not date_str:
            return jsonify({"error": "Date parameter missing"}), 400
        date_obj = datetime.strptime(date_str, "%d-%m-%Y").date()
        df = pd.read_csv(LEADERBOARD_FILE)
        df["date"] = pd.to_datetime(df["date"], errors='coerce').dt.date
        result = df[df["date"] == date_obj].drop_duplicates("store_location").sort_values("ai_score", ascending=False).reset_index(drop=True)
        result["badge"] = ["🥇", "🥈", "🥉"] + [""] * (len(result) - 3)
        return jsonify(result.to_dict(orient="records"))
    except Exception as e:
        return jsonify({"error": str(e)})

# === CHART DATA for AI Leaderboard ===
@app.route('/waste_chart_data', methods=['GET'])
def waste_chart_data():
    try:
        df = pd.read_csv(LEADERBOARD_FILE)
        df["date"] = pd.to_datetime(df["date"], errors='coerce')
        df = df.dropna(subset=["date"])
        chart_data = df.groupby("date")["waste_generated_kg"].sum().reset_index()
        chart_data["date"] = chart_data["date"].dt.strftime("%d-%m-%Y")
        return jsonify({
            "labels": chart_data["date"].tolist(),
            "data": chart_data["waste_generated_kg"].tolist()
        })
    except Exception as e:
        return jsonify({"error": str(e)})

# === MAIN ===
if __name__ == '__main__':
    print("✅ Starting Flask...")
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
