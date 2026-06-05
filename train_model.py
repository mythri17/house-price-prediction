import pandas as pd
from sklearn.linear_model import LinearRegression
import pickle

# Load dataset
df = pd.read_csv("Bengaluru_House_Data.csv")

# Remove extra spaces in column names
df.columns = df.columns.str.strip()

# Select required columns
df = df[['location', 'total_sqft', 'bhk', 'bath', 'price']]

# Remove missing values
df = df.dropna()

# Validation filters
df = df[
    (df['bhk'] <= 8) &
    (df['bath'] <= 6) &
    (df['total_sqft'] >= 1000) &
    (df['total_sqft'] <= 5000)
]

# Convert locations into dummy variables
df = pd.get_dummies(df, columns=['location'])

# Features
X = df.drop('price', axis=1)

# Target
y = df['price']

# Train model
model = LinearRegression()
model.fit(X, y)

# Save model
pickle.dump(model, open("model.pkl", "wb"))
pickle.dump(X.columns.tolist(), open("columns.pkl", "wb"))

print("✅ Model trained successfully")