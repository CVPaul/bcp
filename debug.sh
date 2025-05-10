if [ $# -lt 1 ]; then
    echo ">>> [ERROR]please specify the coin that you want to debug, e.g ETH, BNBUSD_PERP, ..."
    exit 1
fi
crontab -l|grep $1|head -1|awk -F">>" '{print $1"--debug"}'|awk -F"python" '{print $2}'|PYTHONPATH=. xargs python
