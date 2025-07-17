from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import os
import joblib
import pandas as pd
from datetime import datetime
from prophet import Prophet

# ── Configuration ──────────────────────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
app = Flask(
    __name__,
    static_folder=BASE_DIR,     # serve files from this directory
    static_url_path=''          # at the root URL
)
CORS(app)

# ── Load models ────────────────────────────────────────────────────────────────
model        = joblib.load(os.path.join(BASE_DIR, "waste_predictor_model.pkl"))
model_columns= joblib.load(os.path.join(BASE_DIR, "model_columns.pkl"))
demand_model = joblib.load(os.path.join(BASE_DIR, "demand_model.pkl"))
ai_model     = joblib.load(os.path.join(BASE_DIR, "ai_score_model.pkl"))

# ── Serve frontend ─────────────────────────────────────────────────────────────
@app.route('/', methods=['GET'])
def home():
    # will serve BASE_DIR/index.html
    return send_from_directory(BASE_DIR, 'index.html')

# ── Waste Predictor routes ─────────────────────────────────────────────────────
@app.route('/upload_csv', methods=['POST'])
def upload_csv():
    try:
        file = request.files['file']
        df   = pd.read_csv(file)
        required = {"product_id","name","category","stock","expiry_date","store_location","freshness_score"}
        if not required.issubset(df.columns):
            return jsonify(success=False, error="Missing required columns.")

        today = datetime.today().date()
        df['expiry_date'] = pd.to_datetime(df['expiry_date'], errors='coerce')
        df['days_to_expiry'] = df['expiry_date'].apply(lambda x: (x.date()-today).days if pd.notna(x) else pd.NA)
        df['expiry_risk'] = df.apply(lambda r: 1 if pd.notna(r['days_to_expiry']) and r['days_to_expiry']<=2 and r['freshness_score']<0.7 else 0, axis=1)

        def label_status(d):
            if pd.isna(d): return "Invalid Date"
            return "Already Expired" if d<0 else f"{d} day(s) left"
        df['expiry_status'] = df['days_to_expiry'].apply(label_status)

        if 'previous_sales' not in df.columns: df['previous_sales'] = (df['stock']*0.7).astype(int).clip(lower=1)
        if 'temperature_C'  not in df.columns: df['temperature_C'] = 25

        df['daily_demand'] = df.apply(lambda r: round(demand_model.predict([[r['previous_sales'],r['stock'],r['temperature_C']]])[0],2), axis=1)
        df['recommendation'] = df['expiry_risk'].map({1:"Donate",0:"Keep in Stock"})

        recommendations = df[[
            'product_id','name','store_location','category','stock',
            'freshness_score','expiry_status','daily_demand','expiry_risk','recommendation'
        ]].to_dict(orient='records')

        alerts=[]
        for _,r in df.iterrows():
            if r['days_to_expiry']<1: reason="❗ Expiring Today"
            elif r['stock']>50 and r['daily_demand']<10: reason="📉 Overstocked, Low Demand"
            elif r['daily_demand']>80 and r['stock']<20 and r['days_to_expiry']>1: reason="⚡ Demand Surge, Low Stock"
            else: continue
            alerts.append({
                'product_id':r['product_id'],'name':r['name'],'store_location':r['store_location'],
                'category':r['category'],'stock':int(r['stock']),
                'expiry_date': r['expiry_date'].strftime("%d-%m-%Y") if pd.notna(r['expiry_date']) else "",
                'daily_demand':r['daily_demand'],'days_to_expiry':int(r['days_to_expiry']) if pd.notna(r['days_to_expiry']) else None,
                'alert_reason':reason
            })

        return jsonify(success=True, recommendations=recommendations, alerts=alerts)
    except Exception as e:
        return jsonify(success=False, error=str(e))

@app.route('/predict', methods=['POST'])
def predict():
    data = request.get_json()
    query= [data.get(col) for col in model_columns]
    pred = model.predict([query])[0]
    return jsonify(prediction=("High Risk" if pred==1 else "Low Risk"))

@app.route('/forecast_demand', methods=['POST'])
def forecast_demand():
    d = request.get_json()
    val = demand_model.predict([[d['previous_sales'],d['stock'],d['temperature_C']]])[0]
    return jsonify(forecasted_demand=round(val,2))

@app.route('/recommend_action', methods=['POST'])
def recommend_action():
    d = request.get_json()
    exp = model.predict([[d.get(col) for col in model_columns]])[0]
    dem = demand_model.predict([[d['previous_sales'],d['stock'],d['temperature_C']]])[0]
    if exp==1 and dem<20: action="Donate"
    elif exp==1: action="Transfer or Apply Discount"
    else: action="Keep in Stock"
    return jsonify(expiry_risk=int(exp), forecasted_demand=round(dem,2), recommendation=action)

# ── AI Leaderboard setup ──────────────────────────────────────────────────────
LEADER_CSV = os.path.join(BASE_DIR, "data", "ai_leaderboard.csv")
os.makedirs(os.path.dirname(LEADER_CSV), exist_ok=True)
if not os.path.exists(LEADER_CSV):
    pd.DataFrame(columns=[
        "store_location","waste_donated_kg","waste_reduced_kg",
        "waste_generated_kg","date","ai_score"
    ]).to_csv(LEADER_CSV,index=False)

@app.route('/upload_waste_ai', methods=['POST'])
def upload_waste_ai():
    file = request.files['file']
    df   = pd.read_csv(file)
    req  = {"store_location","waste_donated_kg","waste_reduced_kg","waste_generated_kg","date"}
    if not req.issubset(df.columns):
        return jsonify(success=False, error="Missing required columns.")
    df['date'] = pd.to_datetime(df['date'], errors='coerce').dt.date
    df['ai_score'] = ai_model.predict(df[["waste_donated_kg","waste_reduced_kg","waste_generated_kg"]]).round(2)
    df.to_csv(LEADER_CSV, mode='a', index=False, header=False)
    return jsonify(success=True, message="Report uploaded with AI scores!")

@app.route('/ai_daily_leaderboard', methods=['GET'])
def ai_daily_leaderboard():
    df    = pd.read_csv(LEADER_CSV)
    df['date']=pd.to_datetime(df['date'],errors='coerce').dt.date
    today = datetime.today().date()
    daily = df[df['date']==today].drop_duplicates('store_location').sort_values('ai_score',ascending=False).reset_index(drop=True)
    daily['badge']=["🥇","🥈","🥉"]+[""]*(len(daily)-3)
    return jsonify(daily.to_dict(orient='records'))

@app.route('/ai_monthly_leaderboard', methods=['GET'])
def ai_monthly_leaderboard():
    df    = pd.read_csv(LEADER_CSV)
    df['date']=pd.to_datetime(df['date'],errors='coerce')
    now   = datetime.today()
    m     = df[(df['date'].dt.month==now.month)&(df['date'].dt.year==now.year)]
    agg   = m.groupby('store_location').agg({
        'waste_donated_kg':'sum','waste_reduced_kg':'sum',
        'waste_generated_kg':'sum','ai_score':'mean'
    }).reset_index().sort_values('ai_score',ascending=False)
    agg['badge']=["🏆"]+[""]*(len(agg)-1)
    return jsonify(agg.to_dict(orient='records'))

# ── Waste Forecast ─────────────────────────────────────────────────────────────
@app.route('/forecast_waste', methods=['POST'])
def forecast_waste():
    file = request.files.get('file')
    if not file:
        return jsonify(error="No file uploaded"), 400
    df = pd.read_csv(file)
    req= {"store_location","item_name","date","waste_kg"}
    if not req.issubset(df.columns):
        return jsonify(error=f"Missing columns: {req}"), 400

    df['date']=pd.to_datetime(df['date'], format="%d-%m-%Y",errors='coerce')
    df = df.dropna(subset=['date','waste_kg'])
    results=[]
    for (store,item),grp in df.groupby(['store_location','item_name']):
        ts = grp.rename(columns={'date':'ds','waste_kg':'y'})[['ds','y']].sort_values('ds')
        if len(ts)<2: continue
        m = Prophet().fit(ts)
        future = m.make_future_dataframe(periods=7)
        forecast = m.predict(future)[['ds','yhat']].tail(7)
        forecast['ds']=forecast['ds'].dt.strftime("%d-%m-%Y")
        for _,row in forecast.iterrows():
            results.append({
                'store_location':store,
                'item_name':item,
                'date':row['ds'],
                'predicted_waste_kg':round(row['yhat'],2)
            })
    return jsonify(results)

# ── Launch ───────────────────────────────────────────────────────────────────
if __name__ == '__main__':
    # bind to all interfaces on port 5000
    app.run(host='0.0.0.0', port=5000, debug=True)
