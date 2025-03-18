import os
import torch
from torch.utils.data import Dataset
import pandas as pd
from PIL import Image
import sys
sys.path.append('../../')
from tools.visual.inspect import analysis

class VLDataset(Dataset):
    def __init__(self, data_path, image_dir, transform=None):
        self.df = pd.read_pickle(data_path)
        self.image_dir = image_dir
        self.transform = transform

    def __len__(self):
        return len(self.df)

    def __getitem__(self, idx):
        sample = self.df.iloc[idx]
        temp_image_path = os.path.join(self.image_dir, f"vl_{idx}.png")
        
        # Generate visualization and save image
        analysis(sample, save_path=temp_image_path)
        
        # Load image and extract features
        image = Image.open(temp_image_path).convert("RGB")
        text_features = sample[['M1', 'M2', 'M3', 'M4']].values  # Technical indicators
        
        if self.transform:
            image = self.transform(image)
            
        return {
            'image': torch.tensor(image, dtype=torch.float32),
            'text': torch.tensor(text_features, dtype=torch.float32),
            'label': sample['target']  # Target variable for prediction
        }
