#!/usr/bin/env python
#-*- coding:utf-8 -*-


import random
import numpy as np

import torch
import torch.nn as nn
import torch.optim as optim

from collections import deque
from strategy.model.env import TradeEnv


class DQNAgent:
    def __init__(self, state_size, action_size):
        self.state_size = state_size
        self.mid = action_size // 2
        self.action_size = action_size
        self.memory = deque(maxlen=2000)
        self.gamma = 0.95    # discount rate
        self.epsilon = 1.0  # exploration rate
        self.epsilon_min = 0.01
        self.epsilon_decay = 0.999
        self.model = self._build_model()

    def _build_model(self):
        model = nn.Sequential(
            nn.Linear(self.state_size, 24),
            nn.ReLU(),
            nn.Linear(24, 24),
            nn.ReLU(),
            nn.Linear(24, self.action_size)
        )
        return model

    def remember(self, state, action, reward, next_state, done):
        self.memory.append((state, action, reward, next_state, done))

    def act(self, state):
        if np.random.rand() <= self.epsilon:
            return random.randrange(self.action_size) - self.mid
        state = torch.FloatTensor(state).unsqueeze(0)
        q_values = self.model(state)
        return q_values.argmax().item() - self.mid

    def replay(self, batch_size):
        if len(self.memory) < batch_size:
            return
        minibatch = random.sample(self.memory, batch_size)
        states, targets = [], []
        for state, action, reward, next_state, done in minibatch:
            state = torch.FloatTensor(state).unsqueeze(0)
            next_state = torch.FloatTensor(next_state).unsqueeze(0)
            q_values = self.model(state)
            target = q_values.clone().detach()
            if done:
                target[0][action] = reward
            else:
                next_q_values = self.model(next_state)
                target[0][action] = reward + self.gamma * next_q_values.max().item()
            states.append(state)
            targets.append(target)
        states = torch.cat(states)
        targets = torch.cat(targets)
        criterion = nn.MSELoss()
        optimizer = optim.Adam(self.model.parameters())
        optimizer.zero_grad()
        loss = criterion(self.model(states), targets)
        loss.backward()
        optimizer.step()
        if self.epsilon > self.epsilon_min:
            self.epsilon *= self.epsilon_decay

def main():
    histlen = 10
    data_files = [
        'data/real-time.DOGEUSD_PERP.2024-03-27.dat.gz',
        'data/real-time.DOGEUSD_PERP.2024-03-28.dat.gz',
        'data/real-time.DOGEUSD_PERP.2024-03-29.dat.gz',
    ]
    env = TradeEnv(
        'DOGEUSD_PERP', data_files,
        0.005, 0.01, histlen)
    state_size = 2 * histlen
    action_size = 5
    agent = DQNAgent(state_size, action_size)
    batch_size = 32

    episodes = 2000
    model_file = f'model.final.{episodes}.pth'
    for e in range(episodes):
        score = 0
        done = False
        state = env.reset()
        while not done:
            action = -agent.act(state)
            next_state, reward, done = env.step(action)
            # print(env.position, action, reward)
            agent.remember(state, action, reward, next_state, done)
            state = next_state
            agent.replay(batch_size)
            score += reward
        print("episode: {}/{}, score: {}, e: {:.2}"
              .format(e, episodes, score, agent.epsilon))
    torch.save(agent.model.state_dict(), model_file) 


if __name__ == "__main__":
    main()

