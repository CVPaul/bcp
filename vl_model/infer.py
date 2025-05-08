import torch
import pandas as pd

from vl_model import VLModel
from vl_dataset import VLDataset


def main():
    # Load dataset
    dataset = VLDataset(image_dir='data/1h')  # Ensure data path matches your setup
    dataloader = torch.utils.data.DataLoader(
        dataset, batch_size=32, shuffle=False, num_workers=8, pin_memory=True)

    # Initialize model
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = VLModel().to(device)
    model.load_state_dict(torch.load('best_model.pth'))
    model.eval()

    # Inference loop
    idx = 0
    lens = len(dataset)
    predictions = []
    with torch.no_grad():
        for batch in dataloader:
            images = batch['image'].to(device, non_blocking=True)  # Adjust key if dataset uses different input name
            texts = batch['text'].to(device, non_blocking=True)
            outs = model(images, texts)
            # probs = torch.softmax(outs, dim=1)
            predictions.extend(outs.cpu().numpy().tolist())
            idx += images.shape[0]
            print(f'processing {idx} / {lens}')

    # Save results
    df = pd.DataFrame(predictions,columns=['pred'])
    df.to_csv("pred.csv", index=False)

if __name__ == "__main__":
    main()
