#!/usr/bin/env python
#-*- coding:utf-8 -*-


import logging


def get_auth_keys(prefix='strategy'):
    # ED25519 Keys
    api_key = f"{prefix}/api_key.txt"
    with open(api_key) as f:
        api_key = f.read().strip()

    private_key = f"{prefix}/private_key.pem"
    with open(private_key, 'rb') as f:
        private_key = f.read().strip()
    return api_key, private_key


def on_open(self):
    logging.info("ws is connected!")


def on_close(self):
    self.socket_manager.create_ws_connection()
    self.socket_manager.start()
    logging.info(f"try to re-connect to server!")


