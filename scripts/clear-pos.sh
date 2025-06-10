#!/bin/bash

# 设置默认路径
TARGET_DIR="${1:-.}"

# 设置天数（5天）
DAYS=5

echo "正在查找目录：$TARGET_DIR 中 $DAYS 天未修改的文件..."

# 查找满足条件的文件
FILES=$(find "$TARGET_DIR" -type f -mtime +$DAYS)

if [ -z "$FILES" ]; then
    echo "没有找到 $DAYS 天未修改的文件。"
    exit 0
fi

# 遍历每个文件，逐个询问用户是否删除
echo "以下是找到的文件："
echo "$FILES"
echo

for file in $FILES; do
    while true; do
        read -p "是否删除文件 '$file'? [y/n/q]: " yn
        case $yn in
            [Yy]* ) rm "$file"; echo "已删除 $file"; break;;
            [Nn]* ) echo "跳过 $file"; break;;
            [Qq]* ) echo "用户中断。退出脚本。"; exit 0;;
            * ) echo "请输入 y（删除）, n（跳过）或 q（退出）";;
        esac
    done
done

echo "清理完成。"
