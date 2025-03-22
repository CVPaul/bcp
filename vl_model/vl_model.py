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
            nn.Linear(56*56*32, 256),  # After MaxPool2d(2) x2: 224→56 → 56x56 feature map
            # nn.Dropout(0.5),
            # nn.Linear(128, 256)
        )
        
        # Text branch (MLP)
        self.text_encoder = nn.Sequential(
            nn.Linear(24, 32),  # Reduce dimensionality
            nn.ReLU(),
            nn.Dropout(0.3),
            nn.Linear(32, 64)
        )
        
        # Fusion layer
        self.fc = nn.Sequential(
            nn.Linear(256 + 64, 128),  # Combine image+text features
            nn.ReLU(),
            nn.Dropout(0.5),
            nn.Linear(128, 1)  # Final regression output
        )

# Move forward inside the class properly
    def forward(self, image, text):
        batch_size = image.size(0)
        # Reshape 5D (B,9,3,224,224) → 4D (B*9,3,224,224)
        image = image.view(-1, 3, 224, 224)
        image_features = self.image_encoder(image)
        # Reshape back to (B,9,256) then aggregate
        image_features = image_features.view(batch_size, 9, 256)
        image_features = image_features.mean(dim=1)  # (B,256)
        text_features = self.text_encoder(text)
        combined = torch.cat([image_features, text_features], dim=1)
        return self.fc(combined)

    def load_checkpoint(self, checkpoint_path):
        self.load_state_dict(torch.load(checkpoint_path, map_location=torch.device('cpu')))
        self.eval()
