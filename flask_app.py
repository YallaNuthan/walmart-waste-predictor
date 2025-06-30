from flask import Flask, request, jsonify
import joblib
import pandas as pd

import warnings
warnings.filterwarnings("ignore", category=UserWarning)


app = Flask(__name__)

# Load the model and column names
model = joblib.load("waste_risk_model.pkl")
model_columns = joblib.load("model_columns.pkl")

@app.route('/')
def home():
    return "Walmart Waste Risk Predictor API is running!"

@app.route('/predict', methods=['POST'])
def predict():
    try:
        # Get JSON input
        data = request.get_json(force=True)

        # Convert to DataFrame with the correct column order
        input_df = pd.DataFrame([data])
        input_df = input_df.reindex(columns=model_columns, fill_value=0)

        # Make prediction
        prediction = model.predict(input_df)[0]

        # Return response
        return jsonify({
            "waste_risk_prediction": int(prediction),
            "risk_level": "High" if prediction == 1 else "Low"
        })

    except Exception as e:
        return jsonify({"error": str(e)})

# Run the Flask app
@app.route('/test', methods=['POST'])
def test_post():
    return jsonify({"message": "Postman is working!"})

if __name__ == '__main__':
    app.run(debug=True)
