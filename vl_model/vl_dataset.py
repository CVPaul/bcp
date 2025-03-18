import os
import torch
import pandas as pd
from PIL import Image

from torch.utils.data import Dataset

class VLDataset(Dataset):
    def __init__(self, image_dir, transform=None):
        self.image_dir = image_dir
        self.transform = transform
        self.labels = pd.read_csv(f'{image_dir}/label.csv', header=None)

    def __len__(self):
        return len(self.labels)

    def __getitem__(self, idx):
        row = self.labels.iloc[idx]
        path = os.path.join(self.image_dir, f"{row[0]}.png")
        # Load image and extract features
        image = Image.open(path).convert("RGB")
        text_features = row[1:25].values
        if self.transform:
            image = self.transform(image)
        return {
            'image': torch.tensor(image, dtype=torch.float32),
            'text': torch.tensor(text_features, dtype=torch.float32),
            'label': torch.tensor(row[25], dtype=torch.float32) # Target variable for prediction
        }
