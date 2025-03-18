import numpy as np
from scipy.interpolate import UnivariateSpline

def calculate_spline_metrics():
    data = np.load('hist.npy')
    times = data[:, 0]
    prices = data[:, 1]
    
    # 三次样条插值
    spline = UnivariateSpline(times, prices, k=3, s=None)
    
    # 计算一阶和二阶导数
    dydx = spline.derivative()(times)
    d2ydx2 = spline.derivative(n=2)(times)
    
    # 计算曲率
    curvature = np.abs(d2ydx2) / (1 + dydx**2)**1.5
    
    # 返回结果或保存到文件
    return times, prices, dydx, curvature

if __name__ == "__main__":
    times, prices, slope, curvature = calculate_spline_metrics()
    # 保存结果到文件
    np.savez('spline_results.npz', times=times, prices=prices, slope=slope, curvature=curvature)
