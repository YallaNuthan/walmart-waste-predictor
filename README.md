# 🛒 Walmart Food Waste Predictor AI

An AI-powered solution to predict food waste for perishable inventory using machine learning. Built for the **Walmart Sparkathon 2025** under the theme: *"Smart Supply Chain and Sustainability"*.

---

## 🚀 Demo Links

- 🔗 **Frontend (GitHub Pages):**  
  [View Form Interface](https://yourusername.github.io/walmart_waste_predictor/)

- 🔗 **Backend (Render Flask API):**  
  [Flask Predict API](https://your-app-name.onrender.com/predict)

---

## 🧠 How It Works

- A trained ML model predicts **waste risk (0 or 1)** based on input features:
  - Shelf life, stock levels, demand, weather, category, etc.
- HTML form collects user input.
- Flask API handles prediction.
- Result is shown on the same page instantly.

---

## 🧪 Sample Input Format (Sent to Flask)

```json
{
  "shelf_life_days": 6,
  "current_stock": 100,
  "sold_last_7_days": 80,
  "forecasted_demand": 90,
  "temperature_C": 22.5,
  "humidity_%": 60,
  "category_Fruit": 1,
  "category_Meat": 0,
  "category_Vegetable": 0
}
