DATADIR = '../data'
DAY_MS_COUNT = 24 * 3600000

# place order at here
# hedge mode should obey following rules
# Open position:
#   - Long : positionSide=LONG, side=BUY
#   - Short: positionSide=SHORT, side=SELL
# Close position:
#   - Close long position: positionSide=LONG, side=SELL
#   - Close short position: positionSide=SHORT, side=BUY
# GTC - Good Till Cancel 成交为止
# IOC - Immediate or Cancel 无法立即成交(吃单)的部分就撤销
# FOK - Fill or Kill 无法全部立即成交就撤销
# GTX - Good Till Crossing 无法成为挂单方就撤销
# GTD - Good Till Date 在特定时间之前有效，到期自动撤销

# MARKET order response:
{
    'orderId': 10712573971,
    'symbol': 'DOGEUSD_PERP',
    'pair': 'DOGEUSD',
    'status': 'NEW',
    'clientOrderId': '8nzijNdKmBgbiCXtyMUCCS',
    'price': '0',
    'avgPrice': '0.000000',
    'origQty': '1',
    'executedQty': '0',
    'cumQty': '0',
    'cumBase': '0',
    'timeInForce': 'GTC',
    'type': 'MARKET',
    'reduceOnly': False,
    'closePosition': False,
    'side': 'SELL',
    'positionSide': 'SHORT',
    'stopPrice': '0',
    'workingType': 'CONTRACT_PRICE',
    'priceProtect': False,
    'origType': 'MARKET',
    'updateTime': 1712226730949
}

# LIMIT order response
# 实际上价格并没有限制，不满足挂单某种情况下会就等价于market
{
    'orderId': 10712602355,
    'symbol': 'DOGEUSD_PERP',
    'pair': 'DOGEUSD',
    'status': 'NEW',
    'clientOrderId': 'pLobL6zEnXOT3nbzfTONhG',
    'price': '0.176000',
    'avgPrice': '0.000000',
    'origQty': '1',
    'executedQty': '0',
    'cumQty': '0',
    'cumBase': '0',
    'timeInForce': 'GTC',
    'type': 'LIMIT',
    'reduceOnly': False,
    'closePosition': False,
    'side': 'SELL',
    'positionSide': 'SHORT',
    'stopPrice': '0',
    'workingType': 'CONTRACT_PRICE',
    'priceProtect': False,
    'origType': 'LIMIT',
    'updateTime': 1712226952632
}

# STOP Order response
# 对price的要求：[SELL]price/stopPrice > 0.95 否者会报错："Limit price can't be lower than 0.176795"
# stopPrice要求：必须小于当前最新价[SELL]，否者报错：'Order would immediately trigger.'
# 返回内容和上面类似