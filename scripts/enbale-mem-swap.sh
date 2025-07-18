# 1. 创建新的 8GB swap 文件
sudo fallocate -l 8G /swapfile
# 2. 设置权限
sudo chmod 600 /swapfile
# 3. 格式化为 swap 分区
sudo mkswap /swapfile
# 4. 启用新的 swap
sudo swapon /swapfile
# 5. 确保开机自动挂载（这一步只需要执行一次，如果你已经执行过则跳过）
grep -q "/swapfile" /etc/fstab || echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
