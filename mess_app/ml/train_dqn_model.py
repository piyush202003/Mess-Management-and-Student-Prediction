import pandas as pd
import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
import random
from collections import deque
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.model_selection import train_test_split
import os

# ==============================
# Paths
# ==============================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.path.join(BASE_DIR, "synthetic_attendance_dataset_large_with_mealtime.csv")
MODEL_PATH = os.path.join(BASE_DIR, "dqn_mess_model.pth")

# ==============================
# Load Data
# ==============================
df = pd.read_csv(DATA_PATH)

# One-hot encode categorical variables
day_encoder = OneHotEncoder(sparse_output=False)
type_encoder = OneHotEncoder(sparse_output=False)
holiday_encoder = OneHotEncoder(sparse_output=False)
meal_encoder = OneHotEncoder(sparse_output=False)

day_encoded = day_encoder.fit_transform(df[['day_of_week']])
type_encoded = type_encoder.fit_transform(df[['dish_type']])
holiday_encoded = holiday_encoder.fit_transform(df[['holiday']])
meal_encoded = meal_encoder.fit_transform(df[['meal_time']])

# Combine features
X = np.hstack([day_encoded, type_encoded, holiday_encoded, meal_encoded])
y = df[['attended_students']].values

# Scale target variable
scaler = StandardScaler()
y_scaled = scaler.fit_transform(y)

# Split dataset
X_train, X_test, y_train, y_test = train_test_split(X, y_scaled, test_size=0.2, random_state=42)

# ==============================
# Define Q-Network
# ==============================
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

# ==============================
# Replay Memory
# ==============================
class ReplayMemory:
    def __init__(self, capacity):
        self.memory = deque(maxlen=capacity)

    def push(self, state, action, reward, next_state, done):
        self.memory.append((state, action, reward, next_state, done))

    def sample(self, batch_size):
        return random.sample(self.memory, batch_size)

    def __len__(self):
        return len(self.memory)

# ==============================
# DQN Agent
# ==============================
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

# ==============================
# Dish List (Actions)
# ==============================
all_dishes = [
    ("DalRice", "veg", False),
    ("Poha", "veg", False),
    ("Paneer", "veg", False),
    ("Biryani", "nonveg", True),
    ("Chicken Curry", "nonveg", True),
    ("Pulao", "veg", False),
    ("Idli", "veg", False),
    ("Special Sweet", "veg", True),
]

# ==============================
# Training Loop
# ==============================
state_dim = X_train.shape[1]
action_dim = len(all_dishes)
agent = DQNAgent(state_dim, action_dim)
episodes = 1000
batch_size = 32

for episode in range(episodes):
    idx = np.random.randint(0, len(X_train))
    state = X_train[idx]
    total_reward = 0

    for t in range(20):  # simulate steps
        action = agent.act(state)
        next_idx = np.random.randint(0, len(X_train))
        next_state = X_train[next_idx]
        reward = y_train[next_idx][0]
        done = t == 19

        agent.memory.push(state, action, reward, next_state, done)
        state = next_state
        total_reward += reward

        if len(agent.memory) > batch_size:
            batch = agent.memory.sample(batch_size)
            for s, a, r, ns, d in batch:
                s = torch.FloatTensor(s)
                ns = torch.FloatTensor(ns)
                q_values = agent.q_network(s)
                q_value = q_values[a]

                # ✅ FIXED detach() issue
                with torch.no_grad():
                    max_next = agent.target_network(ns).max().detach().item()

                target = r + agent.gamma * max_next * (1 - d)
                loss = (q_value - target) ** 2
                agent.optimizer.zero_grad()
                loss.backward()
                agent.optimizer.step()

        if done:
            break

    agent.epsilon = max(agent.epsilon_min, agent.epsilon * agent.epsilon_decay)

    if episode % 50 == 0:
        agent.update_target()
        print(f"Episode {episode}/{episodes} | Epsilon: {agent.epsilon:.2f} | Reward: {total_reward:.2f}")

# ==============================
# Save Model
# ==============================
torch.save({
    "q_network_state_dict": agent.q_network.state_dict(),
    "target_network_state_dict": agent.target_network.state_dict(),
}, MODEL_PATH)

print("✅ Model retrained and saved at:", MODEL_PATH)
