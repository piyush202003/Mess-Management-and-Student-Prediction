import os
import pandas as pd
import numpy as np
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestRegressor
import torch
import torch.nn as nn
import torch.optim as optim
import random
from collections import deque

# =========================
# Paths
# =========================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.path.join(BASE_DIR, 'synthetic_attendance_dataset_large_with_mealtime.csv')
MODEL_PATH = os.path.join(BASE_DIR, 'dqn_mess_model.pth')

# =========================
# Load & preprocess data
# =========================
df = pd.read_csv(DATA_PATH)
df['holiday'] = df['holiday'].astype(str).str.capitalize()

DAY_COL, TYPE_COL, HOLIDAY_COL, MEAL_COL = ['day_of_week'], ['dish_type'], ['holiday'], ['meal_time']

day_encoder = OneHotEncoder(sparse_output=False, handle_unknown='ignore')
type_encoder = OneHotEncoder(sparse_output=False, handle_unknown='ignore')
holiday_encoder = OneHotEncoder(sparse_output=False, handle_unknown='ignore')
meal_encoder = OneHotEncoder(sparse_output=False, handle_unknown='ignore')

day_encoded = day_encoder.fit_transform(df[DAY_COL])
type_encoded = type_encoder.fit_transform(df[TYPE_COL])
holiday_encoded = holiday_encoder.fit_transform(df[HOLIDAY_COL])
meal_encoded = meal_encoder.fit_transform(df[MEAL_COL])

X = np.hstack([day_encoded, type_encoded, holiday_encoded, meal_encoded])
scaler = StandardScaler()
y = scaler.fit_transform(df[['attended_students']])

X_train, X_temp, y_train, y_temp = train_test_split(X, y, test_size=0.3, random_state=42)
X_val, X_test, y_val, y_test = train_test_split(X_temp, y_temp, test_size=0.5, random_state=42)

rf_model = RandomForestRegressor(n_estimators=100, random_state=42)
rf_model.fit(X_train, y_train.ravel())

# =========================
# DQN Network
# =========================
class QNetwork(nn.Module):
    def __init__(self, input_dim, output_dim):
        super(QNetwork, self).__init__()
        self.fc1 = nn.Linear(input_dim, 128)
        self.fc2 = nn.Linear(128, 128)
        self.fc3 = nn.Linear(128, output_dim)
    def forward(self, x):
        x = torch.relu(self.fc1(x))
        x = torch.relu(self.fc2(x))
        return self.fc3(x)

class ReplayMemory:
    def __init__(self, capacity):
        self.memory = deque(maxlen=capacity)
    def push(self, state, action, reward, next_state, done):
        self.memory.append((state, action, reward, next_state, done))
    def sample(self, batch_size):
        return random.sample(self.memory, batch_size)
    def __len__(self):
        return len(self.memory)

class DQNAgent:
    def __init__(self, state_dim, action_dim, lr=1e-3, gamma=0.99, epsilon=1.0, epsilon_decay=0.995, epsilon_min=0.1):
        self.q_network = QNetwork(state_dim, action_dim)
        self.target_network = QNetwork(state_dim, action_dim)
        self.optimizer = optim.Adam(self.q_network.parameters(), lr=lr)
        self.memory = ReplayMemory(10000)
        self.gamma = gamma
        self.epsilon = epsilon
        self.epsilon_decay = epsilon_decay
        self.epsilon_min = epsilon_min
        self.update_target()
    def update_target(self):
        self.target_network.load_state_dict(self.q_network.state_dict())
    def act(self, state):
        if random.random() < self.epsilon:
            return random.randint(0, self.q_network.fc3.out_features - 1)
        with torch.no_grad():
            q_values = self.q_network(torch.FloatTensor(state).unsqueeze(0))
        return q_values.argmax().item()

# =========================
# Dishes List
# =========================
original_training_dishes = [
    ("DalRice", "veg"), ("Poha", "veg"), ("Paneer", "veg"),
    ("Biryani", "nonveg"), ("Chicken Curry", "nonveg"), ("Pulao", "veg"),
    ("Idli", "veg"), ("Special Sweet", "veg"),
]

# =========================
# Load model
# =========================
state_dim = X_train.shape[1]
action_dim = len(original_training_dishes)
agent = DQNAgent(state_dim, action_dim)

if os.path.exists(MODEL_PATH):
    checkpoint = torch.load(MODEL_PATH, map_location=torch.device('cpu'))
    agent.q_network.load_state_dict(checkpoint['q_network_state_dict'])
    agent.target_network.load_state_dict(checkpoint['target_network_state_dict'])
    agent.epsilon = 0.0

# =========================
# Helper: Prepare Input
# =========================
def _prepare_input(day_of_week, holiday, meal_time, dish_type):
    day_df = pd.DataFrame([[day_of_week]], columns=DAY_COL)
    holiday_df = pd.DataFrame([[holiday]], columns=HOLIDAY_COL)
    meal_df = pd.DataFrame([[meal_time]], columns=MEAL_COL)
    type_df = pd.DataFrame([[dish_type]], columns=TYPE_COL)
    
    day_encoded_input = day_encoder.transform(day_df)
    holiday_encoded_input = holiday_encoder.transform(holiday_df)
    meal_encoded_input = meal_encoder.transform(meal_df)
    type_encoded_input = type_encoder.transform(type_df)

    return np.hstack([day_encoded_input, type_encoded_input, holiday_encoded_input, meal_encoded_input])

# =========================
# Softmax + Repeat-Penalty Recommendation
# =========================
def predict_best_dish(day_of_week, holiday, meal_time, provider_dishes, temperature=1.0, repeat_penalty=0.5):
    """
    Predict best dish for a given day, meal_time, holiday
    provider_dishes: list of tuples (dish_name, dish_type)
    """
    holiday = str(holiday).capitalize()
    q_values_list = []
    for dish_name, dish_type in original_training_dishes:
        X_input = _prepare_input(day_of_week, holiday, meal_time, dish_type)
        with torch.no_grad():
            q_val = agent.q_network(torch.FloatTensor(X_input))
        q_values_list.append((dish_name, dish_type, q_val.max().item()))

    # Apply repeat penalty for dishes that are already offered by provider
    provider_dish_names = [d[0] for d in provider_dishes]
    adjusted_q_values = []
    for name, type_, q in q_values_list:
        penalty = repeat_penalty if name in provider_dish_names else 0
        adjusted_q_values.append((name, type_, q - penalty))

    # Softmax selection
    q_array = np.array([q for _, _, q in adjusted_q_values])
    exp_q = np.exp(q_array / temperature)
    probs = exp_q / exp_q.sum()
    selected_idx = np.random.choice(len(adjusted_q_values), p=probs)
    best_name, best_type, best_q = adjusted_q_values[selected_idx]

    # Predict attendance
    predicted_attendance = predict_attendance_for_dish(day_of_week, holiday, meal_time, best_name, provider_dishes)

    return best_name, best_type, meal_time, round(predicted_attendance, 2)

# =========================
# Attendance Prediction
# =========================
def predict_attendance_for_dish(day_of_week, holiday, meal_time, dish_name, provider_dishes):
    holiday = str(holiday).capitalize()
    dish_type = next((t for d, t in provider_dishes if d == dish_name), None)
    if dish_type is None:
        dish_type = next((t for d, t in original_training_dishes if d == dish_name), None)
    if dish_type is None:
        return 0

    X_input = _prepare_input(day_of_week, holiday, meal_time, dish_type)
    pred_scaled = rf_model.predict(X_input)[0]
    predicted_attendance = scaler.inverse_transform([[pred_scaled]])[0][0]
    return round(predicted_attendance, 2)
