import torch
from torch.utils.data import DataLoader
from vl_dataset import VLDataset
from vl_model import VLModel
from torch.optim import Adam
from torch.nn import MSELoss
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    filename='training.log',
    filemode='w'
)

def main():
    logging.info("Starting training script")
    
    # Configuration
    image_dir = 'data/1h'
    batch_size = 16
    epochs = 10
    learning_rate = 1e-4
    
    # Dataset and Dataloader
    dataset = VLDataset(image_dir)
    dataloader = DataLoader(dataset, batch_size=batch_size, shuffle=True)
    # Model setup
    model = VLModel()
    optimizer = Adam(model.parameters(), lr=learning_rate)
    criterion = MSELoss()
    # Training loop
    for epoch in range(epochs):
        logging.info(f"Epoch {epoch+1}/{epochs}")
        for batch in dataloader:
            images = batch['image']
            text = batch['text']
            labels = batch['label']
            # Forward pass
            outputs = model(images, text)
            loss = criterion(outputs, labels)
            # Backward and optimize
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()
            logging.info(f"Loss: {loss.item():.4f}")
        torch.save(model.state_dict(), f'model_epoch_{epoch}.pth')
        logging.info(f"Model saved after epoch {epoch+1}")
        
if __name__ == '__main__':
    main()
