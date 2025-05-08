from binance.lib.utils import check_required_parameter, check_required_parameters

from binance.constant import _USD_M_API_
from binance.constant import _USD_M_VER_


def new_listen_key(self):
    """Create a ListenKey (USER_STREAM)

    POST /{_USD_M_API_}/{_USD_M_VER_}/listenKey

    https://binance-docs.github.io/apidocs/delivery/en/#listen-key-delivery
    """

    url_path = f"/{_USD_M_API_}/{_USD_M_VER_}/listenKey"
    return self.send_request("POST", url_path)


def renew_listen_key(self, listenKey: str):
    """Ping/Keep-alive a ListenKey (USER_STREAM)

    PUT /{_USD_M_API_}/{_USD_M_VER_}/listenKey

    https://binance-docs.github.io/apidocs/delivery/en/#listen-key-delivery

    Args:
        listenKey (str)
    """
    check_required_parameter(listenKey, "listenKey")

    url_path = f"/{_USD_M_API_}/{_USD_M_VER_}/listenKey"
    return self.send_request("PUT", url_path, {"listenKey": listenKey})


def close_listen_key(self, listenKey: str):
    """Close a ListenKey (USER_STREAM)

    DELETE /{_USD_M_API_}/{_USD_M_VER_}/listenKey

    https://binance-docs.github.io/apidocs/delivery/en/#listen-key-delivery

    Args:
        listenKey (str)
    """
    check_required_parameter(listenKey, "listenKey")

    url_path = f"/{_USD_M_API_}/{_USD_M_VER_}/listenKey"
    return self.send_request("DELETE", url_path, {"listenKey": listenKey})


# Margin
def new_margin_listen_key(self):
    """Create a margin ListenKey (USER_STREAM)

    POST /sapi/v1/userDataStream

    https://binance-docs.github.io/apidocs/delivery/en/#listen-key-margin
    """

    url_path = "/sapi/v1/userDataStream"
    return self.send_request("POST", url_path)


def renew_margin_listen_key(self, listenKey: str):
    """Renew a margin ListenKey (USER_STREAM)

    PUT /sapi/v1/userDataStream

    https://binance-docs.github.io/apidocs/delivery/en/#listen-key-margin

    Args:
        listenKey (str)
    """
    check_required_parameter(listenKey, "listenKey")

    url_path = "/sapi/v1/userDataStream"
    return self.send_request("PUT", url_path, {"listenKey": listenKey})


def close_margin_listen_key(self, listenKey: str):
    """Close a margin ListenKey (USER_STREAM)

    DELETE /sapi/v1/userDataStream

    https://binance-docs.github.io/apidocs/delivery/en/#listen-key-margin

    Args:
        listenKey (str)
    """
    check_required_parameter(listenKey, "listenKey")

    url_path = "/sapi/v1/userDataStream"
    return self.send_request("DELETE", url_path, {"listenKey": listenKey})


# isolated margin
def new_isolated_margin_listen_key(self, symbol: str):
    """Create an isolated margin ListenKey (USER_STREAM)

    POST /sapi/v1/userDataStream/isolated

    https://binance-docs.github.io/apidocs/delivery/en/#listen-key-margin

    Args:
        symbol (str)
    """
    check_required_parameter(symbol, "symbol")

    url_path = "/sapi/v1/userDataStream/isolated"
    return self.send_request("POST", url_path, {"symbol": symbol})


def renew_isolated_margin_listen_key(self, listenKey: str, symbol: str):
    """Renew an isolated ListenKey (USER_STREAM)

    PUT /sapi/v1/userDataStream/isolated

    https://binance-docs.github.io/apidocs/delivery/en/#listen-key-margin

    Args:
        listenKey (str)
        symbol (str)
    """

    check_required_parameters([[listenKey, "listenKey"], [symbol, "symbol"]])

    payload = {"listenKey": listenKey, "symbol": symbol}

    url_path = "/sapi/v1/userDataStream/isolated"
    return self.send_request("PUT", url_path, payload)


def close_isolated_margin_listen_key(self, listenKey: str, symbol: str):
    """Close an isolated margin ListenKey (USER_STREAM)

    DELETE /sapi/v1/userDataStream/isolated

    https://binance-docs.github.io/apidocs/delivery/en/#listen-key-margin

    Args:
        listenKey (str)
        symbol (str)
    """

    check_required_parameters([[listenKey, "listenKey"], [symbol, "symbol"]])

    payload = {"listenKey": listenKey, "symbol": symbol}

    url_path = "/sapi/v1/userDataStream/isolated"
    return self.send_request("DELETE", url_path, payload)
