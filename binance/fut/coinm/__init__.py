from binance.api import API
from binance.constant import _COIN_M_API_


class CoinM(API):
    def __init__(self, api_key=None, api_secret=None, **kwargs):
        if "base_url" not in kwargs:
            kwargs["base_url"] = f"https://{_COIN_M_API_}.binance.com"
        super().__init__(api_key, api_secret, **kwargs)

    # MARKETS
    from binance.fut.coinm._market import ping
    from binance.fut.coinm._market import time
    from binance.fut.coinm._market import exchange_info
    from binance.fut.coinm._market import depth
    from binance.fut.coinm._market import trades
    from binance.fut.coinm._market import historical_trades
    from binance.fut.coinm._market import agg_trades
    from binance.fut.coinm._market import klines
    from binance.fut.coinm._market import ext_klines
    from binance.fut.coinm._market import avg_price
    from binance.fut.coinm._market import ticker_24hr
    from binance.fut.coinm._market import ticker_price
    from binance.fut.coinm._market import book_ticker
    from binance.fut.coinm._market import rolling_window_ticker

    # ACCOUNT (including orders and trades)
    from binance.fut.coinm._trade import new_order_test
    from binance.fut.coinm._trade import new_order
    from binance.fut.coinm._trade import cancel_order
    from binance.fut.coinm._trade import modify_order
    from binance.fut.coinm._trade import cancel_open_orders
    from binance.fut.coinm._trade import get_order
    from binance.fut.coinm._trade import cancel_and_replace
    from binance.fut.coinm._trade import get_open_orders
    from binance.fut.coinm._trade import get_orders
    from binance.fut.coinm._trade import commission_rate
    from binance.fut.coinm._trade import new_oco_order
    from binance.fut.coinm._trade import cancel_oco_order
    from binance.fut.coinm._trade import get_oco_order
    from binance.fut.coinm._trade import get_oco_orders
    from binance.fut.coinm._trade import get_oco_open_orders
    from binance.fut.coinm._trade import account
    from binance.fut.coinm._trade import user_trades
    from binance.fut.coinm._trade import get_order_rate_limit
    from binance.fut.coinm._trade import query_prevented_matches

    # STREAMS
    from binance.fut.coinm._data_stream import new_listen_key
    from binance.fut.coinm._data_stream import renew_listen_key
    from binance.fut.coinm._data_stream import close_listen_key
    from binance.fut.coinm._data_stream import new_margin_listen_key
    from binance.fut.coinm._data_stream import renew_margin_listen_key
    from binance.fut.coinm._data_stream import close_margin_listen_key
    from binance.fut.coinm._data_stream import new_isolated_margin_listen_key
    from binance.fut.coinm._data_stream import renew_isolated_margin_listen_key
    from binance.fut.coinm._data_stream import close_isolated_margin_listen_key

    # MARGIN
    from binance.fut.coinm._margin import borrow_repay
    from binance.fut.coinm._margin import margin_all_assets
    from binance.fut.coinm._margin import margin_all_pairs
    from binance.fut.coinm._margin import margin_pair_index
    from binance.fut.coinm._margin import new_margin_order
    from binance.fut.coinm._margin import cancel_margin_order
    from binance.fut.coinm._margin import margin_transfer_history
    from binance.fut.coinm._margin import borrow_repay_record
    from binance.fut.coinm._margin import margin_interest_history
    from binance.fut.coinm._margin import margin_force_liquidation_record
    from binance.fut.coinm._margin import margin_account
    from binance.fut.coinm._margin import margin_order
    from binance.fut.coinm._margin import margin_open_orders
    from binance.fut.coinm._margin import margin_open_orders_cancellation
    from binance.fut.coinm._margin import margin_all_orders
    from binance.fut.coinm._margin import margin_my_trades
    from binance.fut.coinm._margin import margin_max_borrowable
    from binance.fut.coinm._margin import margin_max_transferable
    from binance.fut.coinm._margin import isolated_margin_account
    from binance.fut.coinm._margin import isolated_margin_all_pairs
    from binance.fut.coinm._margin import toggle_bnbBurn
    from binance.fut.coinm._margin import bnbBurn_status
    from binance.fut.coinm._margin import margin_interest_rate_history
    from binance.fut.coinm._margin import new_margin_oco_order
    from binance.fut.coinm._margin import cancel_margin_oco_order
    from binance.fut.coinm._margin import get_margin_oco_order
    from binance.fut.coinm._margin import get_margin_oco_orders
    from binance.fut.coinm._margin import get_margin_open_oco_orders
    from binance.fut.coinm._margin import cancel_isolated_margin_account
    from binance.fut.coinm._margin import enable_isolated_margin_account
    from binance.fut.coinm._margin import isolated_margin_account_limit
    from binance.fut.coinm._margin import margin_fee
    from binance.fut.coinm._margin import isolated_margin_fee
    from binance.fut.coinm._margin import isolated_margin_tier
    from binance.fut.coinm._margin import margin_order_usage
    from binance.fut.coinm._margin import summary_of_margin_account
    from binance.fut.coinm._margin import cross_margin_collateral_ratio
    from binance.fut.coinm._margin import get_small_liability_exchange_coin_list
    from binance.fut.coinm._margin import get_small_liability_exchange_history
    from binance.fut.coinm._margin import get_a_future_hourly_interest_rate
    from binance.fut.coinm._margin import adjust_cross_margin_max_leverage

    # Staking
    from binance.fut.coinm._staking import staking_product_list
    from binance.fut.coinm._staking import staking_purchase_product
    from binance.fut.coinm._staking import staking_redeem_product
    from binance.fut.coinm._staking import staking_product_position
    from binance.fut.coinm._staking import staking_history
    from binance.fut.coinm._staking import staking_set_auto_staking
    from binance.fut.coinm._staking import staking_product_quota

    # WALLET
    from binance.fut.coinm._wallet import system_status
    from binance.fut.coinm._wallet import coin_info
    from binance.fut.coinm._wallet import account_snapshot
    from binance.fut.coinm._wallet import disable_fast_withdraw
    from binance.fut.coinm._wallet import enable_fast_withdraw
    from binance.fut.coinm._wallet import withdraw
    from binance.fut.coinm._wallet import deposit_history
    from binance.fut.coinm._wallet import withdraw_history
    from binance.fut.coinm._wallet import deposit_address
    from binance.fut.coinm._wallet import account_status
    from binance.fut.coinm._wallet import api_trading_status
    from binance.fut.coinm._wallet import dust_log
    from binance.fut.coinm._wallet import user_universal_transfer
    from binance.fut.coinm._wallet import user_universal_transfer_history
    from binance.fut.coinm._wallet import transfer_dust
    from binance.fut.coinm._wallet import asset_dividend_record
    from binance.fut.coinm._wallet import asset_detail
    from binance.fut.coinm._wallet import trade_fee
    from binance.fut.coinm._wallet import funding_wallet
    from binance.fut.coinm._wallet import user_asset
    from binance.fut.coinm._wallet import api_key_permissions
    from binance.fut.coinm._wallet import bnb_convertible_assets
    from binance.fut.coinm._wallet import convertible_coins
    from binance.fut.coinm._wallet import toggle_auto_convertion
    from binance.fut.coinm._wallet import cloud_mining_trans_history
    from binance.fut.coinm._wallet import convert_transfer
    from binance.fut.coinm._wallet import convert_history
    from binance.fut.coinm._wallet import one_click_arrival_deposit_apply
    from binance.fut.coinm._wallet import balance

    # MINING
    from binance.fut.coinm._mining import mining_algo_list
    from binance.fut.coinm._mining import mining_coin_list
    from binance.fut.coinm._mining import mining_worker
    from binance.fut.coinm._mining import mining_worker_list
    from binance.fut.coinm._mining import mining_earnings_list
    from binance.fut.coinm._mining import mining_bonus_list
    from binance.fut.coinm._mining import mining_statistics_list
    from binance.fut.coinm._mining import mining_account_list
    from binance.fut.coinm._mining import mining_hashrate_resale_request
    from binance.fut.coinm._mining import mining_hashrate_resale_cancellation
    from binance.fut.coinm._mining import mining_hashrate_resale_list
    from binance.fut.coinm._mining import mining_hashrate_resale_details
    from binance.fut.coinm._mining import mining_account_earning

    # SUB-ACCOUNT
    from binance.fut.coinm._sub_account import sub_account_create
    from binance.fut.coinm._sub_account import sub_account_list
    from binance.fut.coinm._sub_account import sub_account_assets
    from binance.fut.coinm._sub_account import sub_account_deposit_address
    from binance.fut.coinm._sub_account import sub_account_deposit_history
    from binance.fut.coinm._sub_account import sub_account_status
    from binance.fut.coinm._sub_account import sub_account_enable_margin
    from binance.fut.coinm._sub_account import sub_account_margin_account
    from binance.fut.coinm._sub_account import sub_account_margin_account_summary
    from binance.fut.coinm._sub_account import sub_account_enable_futures
    from binance.fut.coinm._sub_account import sub_account_futures_transfer
    from binance.fut.coinm._sub_account import sub_account_margin_transfer
    from binance.fut.coinm._sub_account import sub_account_transfer_to_sub
    from binance.fut.coinm._sub_account import sub_account_transfer_to_master
    from binance.fut.coinm._sub_account import sub_account_transfer_sub_account_history
    from binance.fut.coinm._sub_account import sub_account_futures_asset_transfer_history
    from binance.fut.coinm._sub_account import sub_account_futures_asset_transfer
    from binance.fut.coinm._sub_account import sub_account_spot_summary
    from binance.fut.coinm._sub_account import sub_account_universal_transfer
    from binance.fut.coinm._sub_account import sub_account_universal_transfer_history
    from binance.fut.coinm._sub_account import sub_account_futures_account
    from binance.fut.coinm._sub_account import sub_account_futures_account_summary
    from binance.fut.coinm._sub_account import sub_account_futures_position_risk
    from binance.fut.coinm._sub_account import sub_account_spot_transfer_history
    from binance.fut.coinm._sub_account import sub_account_enable_leverage_token
    from binance.fut.coinm._sub_account import managed_sub_account_deposit
    from binance.fut.coinm._sub_account import managed_sub_account_assets
    from binance.fut.coinm._sub_account import managed_sub_account_withdraw
    from binance.fut.coinm._sub_account import sub_account_update_ip_restriction
    from binance.fut.coinm._sub_account import sub_account_api_get_ip_restriction
    from binance.fut.coinm._sub_account import sub_account_api_delete_ip
    from binance.fut.coinm._sub_account import managed_sub_account_get_snapshot
    from binance.fut.coinm._sub_account import managed_sub_account_investor_trans_log
    from binance.fut.coinm._sub_account import managed_sub_account_trading_trans_log
    from binance.fut.coinm._sub_account import managed_sub_account_deposit_address
    from binance.fut.coinm._sub_account import query_sub_account_assets
    from binance.fut.coinm._sub_account import enable_options_for_sub_account
    from binance.fut.coinm._sub_account import query_sub_account_transaction_statistics
    from binance.fut.coinm._sub_account import query_managed_sub_account_margin_asset_details
    from binance.fut.coinm._sub_account import query_managed_sub_account_list
    from binance.fut.coinm._sub_account import (
        query_managed_sub_account_futures_asset_details,
    )
    from binance.fut.coinm._sub_account import futures_position_risk_of_sub_account
    from binance.fut.coinm._sub_account import summary_of_sub_account_s_futures_account
    from binance.fut.coinm._sub_account import detail_on_sub_account_s_futures_account
    from binance.fut.coinm._sub_account import query_managed_sub_account_transfer_log

    # FUTURES
    from binance.fut.coinm._futures import futures_transfer
    from binance.fut.coinm._futures import futures_transfer_history

    # BLVTs
    from binance.fut.coinm._blvt import blvt_info
    from binance.fut.coinm._blvt import subscribe_blvt
    from binance.fut.coinm._blvt import subscription_record
    from binance.fut.coinm._blvt import redeem_blvt
    from binance.fut.coinm._blvt import redemption_record
    from binance.fut.coinm._blvt import user_limit_info

    # BSwap
    from binance.fut.coinm._bswap import bswap_pools
    from binance.fut.coinm._bswap import bswap_liquidity
    from binance.fut.coinm._bswap import bswap_liquidity_add
    from binance.fut.coinm._bswap import bswap_liquidity_remove
    from binance.fut.coinm._bswap import bswap_liquidity_operation_record
    from binance.fut.coinm._bswap import bswap_request_quote
    from binance.fut.coinm._bswap import bswap_swap
    from binance.fut.coinm._bswap import bswap_swap_history
    from binance.fut.coinm._bswap import bswap_pool_configure
    from binance.fut.coinm._bswap import bswap_add_liquidity_preview
    from binance.fut.coinm._bswap import bswap_remove_liquidity_preview
    from binance.fut.coinm._bswap import bswap_unclaimed_rewards
    from binance.fut.coinm._bswap import bswap_claim_rewards
    from binance.fut.coinm._bswap import bswap_claimed_rewards

    # FIAT
    from binance.fut.coinm._fiat import fiat_order_history
    from binance.fut.coinm._fiat import fiat_payment_history

    # C2C
    from binance.fut.coinm._c2c import c2c_trade_history

    # Crypto LOANS
    from binance.fut.coinm._crypto_loan import loan_history
    from binance.fut.coinm._crypto_loan import loan_borrow
    from binance.fut.coinm._crypto_loan import loan_borrow_history
    from binance.fut.coinm._crypto_loan import loan_ongoing_orders
    from binance.fut.coinm._crypto_loan import loan_repay
    from binance.fut.coinm._crypto_loan import loan_repay_history
    from binance.fut.coinm._crypto_loan import loan_adjust_ltv
    from binance.fut.coinm._crypto_loan import loan_adjust_ltv_history
    from binance.fut.coinm._crypto_loan import loan_vip_ongoing_orders
    from binance.fut.coinm._crypto_loan import loan_vip_repay
    from binance.fut.coinm._crypto_loan import loan_vip_repay_history
    from binance.fut.coinm._crypto_loan import loan_vip_collateral_account
    from binance.fut.coinm._crypto_loan import loan_loanable_data
    from binance.fut.coinm._crypto_loan import loan_collateral_data
    from binance.fut.coinm._crypto_loan import loan_collateral_rate
    from binance.fut.coinm._crypto_loan import loan_customize_margin_call
    from binance.fut.coinm._crypto_loan import flexible_loan_adjust_ltv
    from binance.fut.coinm._crypto_loan import flexible_loan_assets_data
    from binance.fut.coinm._crypto_loan import flexible_loan_borrow_history
    from binance.fut.coinm._crypto_loan import flexible_loan_borrow
    from binance.fut.coinm._crypto_loan import flexible_loan_collateral_assets_data
    from binance.fut.coinm._crypto_loan import flexible_loan_ltv_adjustment_history
    from binance.fut.coinm._crypto_loan import flexible_loan_ongoing_orders
    from binance.fut.coinm._crypto_loan import flexible_loan_repay
    from binance.fut.coinm._crypto_loan import flexible_loan_repayment_history

    # PAY
    from binance.fut.coinm._pay import pay_history

    # CONVERT
    from binance.fut.coinm._convert import list_all_convert_pairs
    from binance.fut.coinm._convert import query_order_quantity_precision_per_asset
    from binance.fut.coinm._convert import send_quote_request
    from binance.fut.coinm._convert import accept_quote
    from binance.fut.coinm._convert import order_status
    from binance.fut.coinm._convert import get_convert_trade_history

    # REBATE
    from binance.fut.coinm._rebate import rebate_spot_history

    # NFT
    from binance.fut.coinm._nft import nft_transaction_history
    from binance.fut.coinm._nft import nft_deposit_history
    from binance.fut.coinm._nft import nft_withdraw_history
    from binance.fut.coinm._nft import nft_asset

    # Gift Card (Binance Code in the API documentation)
    from binance.fut.coinm._gift_card import gift_card_create_code
    from binance.fut.coinm._gift_card import gift_card_redeem_code
    from binance.fut.coinm._gift_card import gift_card_verify_code
    from binance.fut.coinm._gift_card import gift_card_rsa_public_key
    from binance.fut.coinm._gift_card import gift_card_buy_code
    from binance.fut.coinm._gift_card import gift_card_token_limit

    # Portfolio Margin
    from binance.fut.coinm._portfolio_margin import portfolio_margin_account
    from binance.fut.coinm._portfolio_margin import portfolio_margin_collateral_rate
    from binance.fut.coinm._portfolio_margin import portfolio_margin_bankruptcy_loan_amount
    from binance.fut.coinm._portfolio_margin import portfolio_margin_bankruptcy_loan_repay
    from binance.fut.coinm._portfolio_margin import (
        query_classic_portfolio_margin_negative_balance_interest_history,
    )
    from binance.fut.coinm._portfolio_margin import query_portfolio_margin_asset_index_price
    from binance.fut.coinm._portfolio_margin import fund_auto_collection
    from binance.fut.coinm._portfolio_margin import bnb_transfer
    from binance.fut.coinm._portfolio_margin import change_auto_repay_futures_status
    from binance.fut.coinm._portfolio_margin import get_auto_repay_futures_status
    from binance.fut.coinm._portfolio_margin import repay_futures_negative_balance
    from binance.fut.coinm._portfolio_margin import fund_collection_by_asset

    # Simple Earn
    from binance.fut.coinm._simple_earn import get_simple_earn_flexible_product_list
    from binance.fut.coinm._simple_earn import get_simple_earn_locked_product_list
    from binance.fut.coinm._simple_earn import subscribe_flexible_product
    from binance.fut.coinm._simple_earn import subscribe_locked_product
    from binance.fut.coinm._simple_earn import redeem_flexible_product
    from binance.fut.coinm._simple_earn import redeem_locked_product
    from binance.fut.coinm._simple_earn import get_flexible_product_position
    from binance.fut.coinm._simple_earn import get_locked_product_position
    from binance.fut.coinm._simple_earn import simple_account
    from binance.fut.coinm._simple_earn import get_flexible_subscription_record
    from binance.fut.coinm._simple_earn import get_locked_subscription_record
    from binance.fut.coinm._simple_earn import get_flexible_redemption_record
    from binance.fut.coinm._simple_earn import get_locked_redemption_record
    from binance.fut.coinm._simple_earn import get_flexible_rewards_history
    from binance.fut.coinm._simple_earn import get_locked_rewards_history
    from binance.fut.coinm._simple_earn import set_flexible_auto_subscribe
    from binance.fut.coinm._simple_earn import set_locked_auto_subscribe
    from binance.fut.coinm._simple_earn import get_flexible_personal_left_quota
    from binance.fut.coinm._simple_earn import get_locked_personal_left_quota
    from binance.fut.coinm._simple_earn import get_flexible_subscription_preview
    from binance.fut.coinm._simple_earn import get_locked_subscription_preview
    from binance.fut.coinm._simple_earn import get_rate_history
    from binance.fut.coinm._simple_earn import get_collateral_record

    # Auto-Invest
    from binance.fut.coinm._auto_invest import get_target_asset_list
    from binance.fut.coinm._auto_invest import get_target_asset_roi_data
    from binance.fut.coinm._auto_invest import query_all_source_asset_and_target_asset
    from binance.fut.coinm._auto_invest import query_source_asset_list
    from binance.fut.coinm._auto_invest import change_plan_status
    from binance.fut.coinm._auto_invest import get_list_of_plans
    from binance.fut.coinm._auto_invest import query_holding_details_of_the_plan
    from binance.fut.coinm._auto_invest import query_subscription_transaction_history
    from binance.fut.coinm._auto_invest import query_index_details
    from binance.fut.coinm._auto_invest import query_index_linked_plan_position_details
    from binance.fut.coinm._auto_invest import one_time_transaction
    from binance.fut.coinm._auto_invest import query_one_time_transaction_status
    from binance.fut.coinm._auto_invest import index_linked_plan_redemption
    from binance.fut.coinm._auto_invest import get_index_linked_plan_redemption_history
    from binance.fut.coinm._auto_invest import index_linked_plan_rebalance_details
