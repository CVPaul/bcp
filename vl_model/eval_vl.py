import argparse
import torch
from vl_model import VLModel
from vl_dataset import VLDataset
from torch.utils.data import DataLoader

def main(checkpoint_path, data_dir):
    # Initialize model and load checkpoint
    model = VLModel()
    model.load_checkpoint(checkpoint_path)
    model.eval()

    # Load test dataset
    test_dataset = VLDataset(data_dir, split='test')
    test_loader = DataLoader(test_dataset, batch_size=32, shuffle=False)

    # Evaluation metrics
    total_loss = 0.0
    criterion = torch.nn.MSELoss()

    with torch.no_grad():
        for batch in test_loader:
            images, texts, targets = batch
            outputs = model(images, texts)
            loss = criterion(outputs, targets)
            total_loss += loss.item() * images.size(0)

    avg_loss = total_loss / len(test_dataset)
    print(f"Average Test Loss: {avg_loss:.4f}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Evaluate VL Model")
    parser.add_argument("checkpoint", type=str, help="Path to model checkpoint file")
    parser.add_argument("--data_dir", type=str, default="data/", help="Directory containing test data")
    args = parser.parse_args()
    main(args.checkpoint, args.data_dir)
