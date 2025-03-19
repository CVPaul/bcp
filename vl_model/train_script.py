import torch
from torch.utils.data import DataLoader
from vl_model import VLModel
from vl_dataset import VLDataset

# 定义训练函数
def train():
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    model = VLModel().to(device)
    criterion = torch.nn.MSELoss()
    optimizer = torch.optim.AdamW(model.parameters(), lr=1e-3, weight_decay=1e-4)
    scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(optimizer, 'min')
    dataset = VLDataset(image_dir='data/1h')
    dataloader = DataLoader(dataset, batch_size=16, shuffle=True, num_workers=4)

    for epoch in range(50):
        model.train()
        train_loss = 0
        for batch in dataloader:
            images, text, labels = batch['image'].to(device), batch['text'].to(device), batch['label'].to(device)
            optimizer.zero_grad()
            outputs = model(images, text)
            loss = criterion(outputs, labels.unsqueeze(1))
            loss.backward()
            optimizer.step()
            train_loss += loss.item()

        # 验证逻辑（需用户补充验证集）
        # 临时注释掉调度器调用以避免NameError
        # scheduler.step(val_loss)
        print(f'Epoch {epoch+1}, Loss: {train_loss/len(dataloader)}')

if __name__ == '__main__':
    train()
