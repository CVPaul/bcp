import torch
from torch.utils.data import DataLoader, Subset
from vl_model import VLModel
from vl_dataset import VLDataset
from torch.optim import AdamW
from torch.nn import MSELoss
from torch.optim.lr_scheduler import ReduceLROnPlateau
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
    batch_size = 24
    epochs = 20
    learning_rate = 1e-3
    num_workers = 8
    pin_memory = True
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

    # Dataset and Dataloaders
    dataset = VLDataset(image_dir=image_dir)
    train_size = int(0.8 * len(dataset))
    val_size = len(dataset) - train_size
    train_dataset = Subset(dataset, range(0, train_size))                                
    val_dataset = Subset(dataset, range(train_size, len(dataset)))

    train_loader = DataLoader(
        train_dataset, batch_size=batch_size, shuffle=True,
        num_workers=num_workers, pin_memory=pin_memory)
    val_loader = DataLoader(
        val_dataset, batch_size=batch_size, shuffle=False,
        num_workers=num_workers, pin_memory=pin_memory)

    # Model setup
    model = VLModel().to(device)
    optimizer = AdamW(model.parameters(), lr=learning_rate, weight_decay=1e-4)
    criterion = MSELoss()
    scheduler = ReduceLROnPlateau(optimizer, 'min', patience=2)

    best_val_loss = float('inf')

    for epoch in range(epochs):
        logging.info(f"Epoch {epoch+1}/{epochs}")

        # Training
        model.train()
        train_loss = 0.0
        for batch in train_loader:
            images = batch['image'].to(device)
            text = batch['text'].to(device)
            labels = batch['label'].to(device)

            optimizer.zero_grad()
            outputs = model(images, text)
            loss = criterion(outputs, labels.unsqueeze(1))
            loss.backward()
            optimizer.step()
            train_loss += loss.item()

        avg_train_loss = train_loss / len(train_loader)
        logging.info(f"Train Loss: {avg_train_loss:.8f}")

        # Validation
        model.eval()
        val_loss = 0.0
        with torch.no_grad():
            for batch in val_loader:
                images = batch['image'].to(device, non_blocking=True)
                text = batch['text'].to(device, non_blocking=True)
                labels = batch['label'].to(device, non_blocking=True)

                outputs = model(images, text)
                loss = criterion(outputs, labels.unsqueeze(1))
                val_loss += loss.item()

        avg_val_loss = val_loss / len(val_loader)
        logging.info(f"Validation Loss: {avg_val_loss:.8f}")

        # Scheduler step
        scheduler.step(avg_val_loss)

        # Save model
        # torch.save(model.state_dict(), f'model_epoch_{epoch+1}.pth')
        # logging.info(f"Model saved after epoch {epoch+1}")

        # Track best model
        if avg_val_loss < best_val_loss:
            best_val_loss = avg_val_loss
            torch.save(model.state_dict(), 'best_model.pth')
            logging.info("Best model updated")

    logging.info("Training completed")

if __name__ == '__main__':
    main()
