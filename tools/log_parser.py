import sys
import json
import ast
import pandas as pd


orders = []
for line in sys.stdin:
    try:
        order = line.split('ORDER|')[-1]
        order = ast.literal_eval(order)
        orders.append(order)
    except:
        pass

df = pd.DataFrame(orders)
df['direction'] = df.side.apply(lambda x: 1 if x == 'BUY' else -1)
df['pos'] = df.direction.cumsum()
df['fprice'] = df['avgPrice'].astype(float)
df['gross'] = df.pos * df.fprice.diff().shift(-1)
df['gross-net'] = df.gross.cumsum()
df['commis'] = df.direction.abs() * df['fprice'] * 2e-4
df['net'] = df['gross'] - df['commis']
df['net-cum'] = df.net.cumsum()
print(df)
