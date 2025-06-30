from flask_cors import CORS
from flask import Flask, request, jsonify
import joblib
import numpy as np
import os

# Load the trained model and columns
model = joblib.load("waste_predictor_model.pkl")
model_columns = joblib.load("model_columns.pkl")

app = Flask(__name__)
CORS(app)
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


if __name__ == '__main__':
    # This is the part that fixes the Render port issue
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
