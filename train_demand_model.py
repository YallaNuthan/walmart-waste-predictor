import pandas as pd
from sklearn.linear_model import LinearRegression
import joblib

# Step 1: Sample dummy data
data = pd.DataFrame({
    'previous_sales': [100, 120, 80, 60, 90],
    'stock': [200, 180, 220, 250, 210],
    'temperature_C': [24, 26, 22, 28, 25],
    'forecast_demand': [110, 130, 90, 75, 100]
})

# Step 2: Features and target
X = data[['previous_sales', 'stock', 'temperature_C']]
y = data['forecast_demand']

# Step 3: Train model
model = LinearRegression()
model.fit(X, y)

# Step 4: Save model as demand_model.pkl
joblib.dump(model, 'demand_model.pkl')

print("✅ demand_model.pkl saved successfully.")
