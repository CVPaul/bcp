import requests

__version__ = "3.5.1"
api_key = None

session = requests.Session()
session.headers.update(
    {
        "Content-Type": "application/json;charset=utf-8",
        "User-Agent": "binance-connector-python/" + __version__,
        "X-MBX-APIKEY": api_key,
    }
)
params = {'url': 'https://dapi.binance.com/dapi/v1/klines', 'params': 'symbol=DOGEUSD_PERP&interval=8h&limit=135'}

print(session.get(**params))
import requests
import dns.resolver
# import pandas as pd


def dns_resolve(domain):
    # 创建一个 DNS 解析器对象，并手动指定 DNS 服务器
    resolver = dns.resolver.Resolver(configure=False)
    resolver.nameservers = ['114.114.114.114']

    # 查询 A 记录
    records = []
    try:
        answers = resolver.resolve(domain, 'A')
        for rdata in answers:
            records.append(rdata.address)
    except dns.resolver.NoAnswer:
        pass
    return records


ip = None
for domain in ['baidu.com', 'binance.com', 'dapi.binance.com']:
    ip = dns_resolve(domain)[0]
    print(domain, ip)