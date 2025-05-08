#!/usr/bin/env python
#-*- coding:utf-8 -*-


import os
import json
import logging
import subprocess as sb


CWD = os.path.dirname(__file__)


def load_api_keys(which='li'):
    with open(f'{CWD}/{which}.api.txt') as fp:
        api_key = fp.read().strip() 
    with open(f'{CWD}/{which}.prv.txt') as fp:
        private_key = fp.read().strip()
    return api_key, private_key


def load_api_keys1():
    path = f'{CWD}/config.json'
    with open(path, 'r') as f:
        config = json.load(f)
        config["API Secret"] = f'{CWD}/secret.txt'
        api_key = config['API Key']
        private_key = config['API Secret']
        if os.path.exists(private_key):
            with open(private_key, 'r') as f:
                private_key = f.read().strip()
    return api_key, private_key


def get_auth_keys(src='file'):
    # ED25519 Keys
    stt_lin = "-----BEGIN PRIVATE KEY-----"
    end_lin = "-----END PRIVATE KEY-----"
    if src == 'file':
        prefix = 'config'
        api_key = f"{prefix}/api_key.txt"
        with open(api_key) as f:
            api_key = f.read().strip()
        prv_key = f"{prefix}/private_key.pem"
        with open(prv_key, 'r') as f:
            prv_key = f.read().strip()
    elif src == 'env':
        api_key = os.environ.get('API_KEY')
        prv_key = os.environ.get('PRV_KEY')
        prv_key = f'{stt_lin}\n{prv_key}\n{end_lin}'
    else:
        raise RuntimeError(f'unsupported src:{src}')
    return api_key, prv_key


def on_open(self):
    logging.info("CONNECTED|snapshot={self.ctx.snapshot}")


def on_close(self):
    logging.warning("DISCONNECTED|snapshot={self.ctx.snapshot}")
    script = f'./status/{self.ctx.stgname}.sh'
    os.execv(script, ['sh', script])
