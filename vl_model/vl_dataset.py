import os
import torch
import pandas as pd
from PIL import Image
from torchvision import transforms

from torch.utils.data import Dataset

class VLDataset(Dataset):
    def __init__(self, image_dir, transform=None):
        self.image_dir = image_dir
        if transform is None:
            self.transform = transforms.Compose([
                transforms.ToTensor(),
            ])
        else:
            self.transform = transform
        self.labels = pd.read_csv(f'{image_dir}/label.csv', header=None)

    def __len__(self):
        return len(self.labels)

    def __getitem__(self, idx):
        row = self.labels.iloc[idx]
        path = os.path.join(self.image_dir, f"{int(row[0])}.png")
        # Load image and extract features
        image = Image.open(path).convert("RGB")
        patches = []
        for i in range(3):
            for j in range(3):
                left = j * 224
                upper = i * 224
                right = left + 224
                lower = upper + 224
                patch = image.crop((left, upper, right, lower))
                if self.transform:
                    patch = self.transform(patch)
                patches.append(patch)
        image_tensor = torch.stack(patches, dim=0)
        return {
            'image': image_tensor,
            'text': torch.tensor(row[1:25].values, dtype=torch.float32),
            'label': torch.tensor(row[25], dtype=torch.float32) # Target variable for prediction
        }
