from flask_cors import CORS
from flask import Flask, request, jsonify, send_from_directory
import joblib
import os
import pandas as pd
from datetime import datetime
from prophet import Prophet

# ─── App Setup ────────────────────────────────────────────────────────────────
# Serve built frontend from the "frontend" folder
app = Flask(__name__, static_folder='frontend', static_url_path='/')
CORS(app)

# ─── Load Models ───────────────────────────────────────────────────────────────
model = joblib.load("waste_predictor_model.pkl")
model_columns = joblib.load("model_columns.pkl")
demand_model = joblib.load("demand_model.pkl")
ai_model = joblib.load("ai_score_model.pkl")

# ─── In–Memory State ───────────────────────────────────────────────────────────
last_recommendation_df = pd.DataFrame()
LEADERBOARD_FILE = "data/ai_leaderboard.csv"
if not os.path.exists(LEADERBOARD_FILE):
    os.makedirs("data", exist_ok=True)
    pd.DataFrame(columns=[
        "store_location", "waste_donated_kg", "waste_reduced_kg",
        "waste_generated_kg", "date", "ai_score"
    ]).to_csv(LEADERBOARD_FILE, index=False)

# ─── SMART BULK RECOMMENDATIONS ───────────────────────────────────────────────
@app.route('/upload_csv', methods=['POST'])
def upload_csv():
    global last_recommendation_df
    try:
        file = request.files['file']
        df = pd.read_csv(file)

        required = {
            "product_id","name","category","stock",
            "expiry_date","store_location","freshness_score"
        }
        if not required.issubset(df.columns):
            return jsonify(success=False, error="Missing required columns."), 400

        today = datetime.today().date()
        df["expiry_date"] = pd.to_datetime(df["expiry_date"], errors='coerce')
        df["days_to_expiry"] = df["expiry_date"].apply(
            lambda x: (x.date() - today).days if pd.notna(x) else pd.NA
        )

        df["expiry_risk"] = df.apply(
            lambda r: 1
                if pd.notna(r["days_to_expiry"])
                   and r["days_to_expiry"] <= 2
                   and r["freshness_score"] < 0.7
                else 0,
            axis=1
        )
        df["expiry_status"] = df["days_to_expiry"].apply(
            lambda d: "Invalid Date"
                if pd.isna(d)
                else ("Already Expired" if d < 0 else f"{d} day(s) left")
        )

        if 'previous_sales' not in df:
            df['previous_sales'] = (df['stock'] * 0.7).astype(int).clip(lower=1)
        if 'temperature_C' not in df:
            df['temperature_C'] = 25

        df["daily_demand"] = df.apply(
            lambda r: round(
                demand_model.predict([[r.previous_sales, r.stock, r.temperature_C]])[0], 2
            ),
            axis=1
        )
        df["recommendation"] = df["expiry_risk"].map({1: "Donate", 0: "Keep in Stock"})

        last_recommendation_df = df.copy()

        alerts_df = df[
            (df.days_to_expiry < 1) |
            ((df.stock > 50) & (df.daily_demand < 10)) |
            ((df.daily_demand > 80) & (df.stock < 20) & (df.days_to_expiry > 1))
        ].copy()
        alerts_df["alert_reason"] = alerts_df.apply(
            lambda r: "❗ Expiring Today"
                if r.days_to_expiry < 1 else
                ("📉 Overstocked, Low Demand"
                    if r.stock > 50 and r.daily_demand < 10 else
                    ("⚡ Demand Surge, Low Stock"
                        if r.daily_demand > 80 and r.stock < 20 else
                        "Unknown")),
            axis=1
        )
        alerts_df["expiry_date"] = alerts_df["expiry_date"].dt.strftime("%d-%m-%Y")

        recommendations = df[[
            "product_id","name","store_location","category","stock",
            "freshness_score","expiry_status","daily_demand",
            "expiry_risk","recommendation"
        ]].to_dict(orient="records")
        alerts = alerts_df[[
            "product_id","name","store_location","category","stock",
            "expiry_date","daily_demand","days_to_expiry","alert_reason"
        ]].to_dict(orient="records")

        return jsonify(success=True, recommendations=recommendations, alerts=alerts)
    except Exception as e:
        return jsonify(success=False, error=str(e)), 500

# ─── CHART DATA ────────────────────────────────────────────────────────────────
@app.route('/chart_smart_bulk', methods=['GET'])
def chart_smart_bulk():
    if last_recommendation_df.empty:
        return jsonify(error="No data uploaded yet."), 400
    grouped = last_recommendation_df.groupby("category")["stock"].sum().reset_index()
    return jsonify(labels=grouped.category.tolist(), data=grouped.stock.tolist())

@app.route('/combined_chart_data', methods=['GET'])
def combined_chart_data():
    result = {}
    if not last_recommendation_df.empty:
        gb = last_recommendation_df.groupby("category")["stock"].sum().reset_index()
        result["bulk_chart"] = {"labels": gb.category.tolist(), "data": gb.stock.tolist()}
    else:
        result["bulk_chart"] = {"labels": [], "data": []}

    if os.path.exists(LEADERBOARD_FILE):
        df = pd.read_csv(LEADERBOARD_FILE)
        df["date"] = pd.to_datetime(df["date"], errors='coerce')
        fc = df.groupby("date")["waste_generated_kg"].sum().reset_index()
        fc["date"] = fc["date"].dt.strftime("%d-%m-%Y")
        result["forecast_chart"] = {"labels": fc.date.tolist(), "data": fc.waste_generated_kg.tolist()}
    else:
        result["forecast_chart"] = {"labels": [], "data": []}

    return jsonify(result)

# ─── RISK & DEMAND ────────────────────────────────────────────────────────────
@app.route('/predict', methods=['POST'])
def predict():
    try:
        js = request.json
        vals = [js[col] for col in model_columns]
        pred = model.predict([vals])[0]
        return jsonify(prediction="High Risk" if pred else "Low Risk")
    except Exception as e:
        return jsonify(error=str(e)), 400

@app.route('/forecast_demand', methods=['POST'])
def forecast_demand():
    try:
        js = request.json
        f = [js['previous_sales'], js['stock'], js['temperature_C']]
        val = round(demand_model.predict([f])[0], 2)
        return jsonify(forecasted_demand=val)
    except Exception as e:
        return jsonify(error=str(e)), 400

# ─── WASTE FORECAST ───────────────────────────────────────────────────────────
@app.route('/forecast_waste', methods=['POST'])
def forecast_waste():
    try:
        file = request.files.get('file')
        if not file:
            return jsonify(error="No file uploaded"), 400
        df = pd.read_csv(file)
        req = {"store_location","item_name","date","waste_kg"}
        if not req.issubset(df.columns):
            return jsonify(error=f"Missing columns: {req}"), 400
        df['date'] = pd.to_datetime(df['date'], format="%d-%m-%Y", errors='coerce')
        df = df.dropna(subset=['date','waste_kg'])
        df['waste_kg'] = pd.to_numeric(df['waste_kg'], errors='coerce')
        results = []
        for (store,item), grp in df.groupby(['store_location','item_name']):
            grp2 = grp.rename(columns={'date':'ds','waste_kg':'y'}).sort_values('ds')
            if len(grp2) < 2: continue
            m = Prophet().fit(grp2[['ds','y']])
            fc = m.predict(m.make_future_dataframe(periods=7))[['ds','yhat']].tail(7)
            fc['ds'] = fc['ds'].dt.strftime("%d-%m-%Y")
            for _,r in fc.iterrows():
                results.append({
                    "store_location": store,
                    "item_name": item,
                    "date": r['ds'],
                    "predicted_waste_kg": round(r['yhat'], 2)
                })
        return jsonify(results)
    except Exception as e:
        return jsonify(error=str(e)), 500

# ─── AI LEADERBOARD ───────────────────────────────────────────────────────────
@app.route('/upload_waste_ai', methods=['POST'])
def upload_waste_ai():
    try:
        file = request.files['file']
        df = pd.read_csv(file)
        req = {"store_location","waste_donated_kg","waste_reduced_kg","waste_generated_kg","date"}
        if not req.issubset(df.columns):
            return jsonify(success=False, error="Missing required columns"), 400
        df['date'] = pd.to_datetime(df['date'], format="%d-%m-%Y", errors='coerce').dt.date
        df['ai_score'] = ai_model.predict(df[["waste_donated_kg","waste_reduced_kg","waste_generated_kg"]]).round(2)
        df.to_csv(LEADERBOARD_FILE, mode='a', index=False, header=False)
        return jsonify(success=True, message="Report uploaded with AI scores!")
    except Exception as e:
        return jsonify(success=False, error=str(e)), 500

@app.route('/ai_daily_leaderboard', methods=['GET'])
def ai_daily_leaderboard():
    try:
        df = pd.read_csv(LEADERBOARD_FILE)
        df['date'] = pd.to_datetime(df['date'], errors='coerce').dt.date
        today = datetime.today().date()
        daily = df[df['date']==today].drop_duplicates('store_location').sort_values('ai_score', ascending=False)
        badges = ["🥇","🥈","🥉"] + [""]*(len(daily)-3)
        daily['badge'] = badges
        return jsonify(daily.to_dict(orient='records'))
    except Exception as e:
        return jsonify(error=str(e)), 500

@app.route('/ai_monthly_leaderboard', methods=['GET'])
def ai_monthly_leaderboard():
    try:
        df = pd.read_csv(LEADERBOARD_FILE)
        df['date'] = pd.to_datetime(df['date'], errors='coerce').dt.date
        now = datetime.today()
        df = df[df['date'].apply(lambda d: d.month==now.month and d.year==now.year)]
        monthly = df.groupby('store_location').agg({
            'waste_donated_kg':'sum','waste_reduced_kg':'sum',
            'waste_generated_kg':'sum','ai_score':'mean'
        }).reset_index().sort_values('ai_score',ascending=False)
        monthly['badge'] = ["🏆"] + [""]*(len(monthly)-1)
        return jsonify(monthly.to_dict(orient='records'))
    except Exception as e:
        return jsonify(error=str(e)), 500

@app.route('/ai_leaderboard_by_date', methods=['GET'])
def ai_leaderboard_by_date():
    try:
        date_str = request.args.get('date')
        if not date_str:
            return jsonify(error="Date parameter missing"), 400
        target = datetime.strptime(date_str,"%d-%m-%Y").date()
        df = pd.read_csv(LEADERBOARD_FILE)
        df['date'] = pd.to_datetime(df['date'], errors='coerce').dt.date
        result = df[df['date']==target].drop_duplicates('store_location').sort_values('ai_score',ascending=False)
        badges = ["🥇","🥈","🥉"] + [""]*(len(result)-3)
        result['badge'] = badges
        return jsonify(result.to_dict(orient='records'))
    except Exception as e:
        return jsonify(error=str(e)), 500

# ─── App Entry Point ───────────────────────────────────────────────────────────
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)
