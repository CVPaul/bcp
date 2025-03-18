import torch
import torch.nn as nn
import torch.nn.functional as F

class VLModel(nn.Module):
    def __init__(self):
        super(VLModel, self).__init__()
        # Image branch (CNN)
        self.image_encoder = nn.Sequential(
            nn.Conv2d(3, 16, kernel_size=3, padding=1),
            nn.ReLU(),
            nn.MaxPool2d(2),
            nn.Conv2d(16, 32, kernel_size=3, padding=1),
            nn.ReLU(),
            nn.MaxPool2d(2),
            nn.Flatten(),
            nn.Linear(32*56*56, 256)  # Assuming 224x224 input images
        )
        
        # Text branch (MLP)
        self.text_encoder = nn.Sequential(
            nn.Linear(4, 64),  # 4 technical indicators
            nn.ReLU(),
            nn.Linear(64, 128)
        )
        
        # Fusion layer
        self.fc = nn.Linear(256 + 128, 1)  # Regression output

    def forward(self, image, text):
        image_features = self.image_encoder(image)
        text_features = self.text_encoder(text)
        combined = torch.cat([image_features, text_features], dim=1)
        return self.fc(combined)
