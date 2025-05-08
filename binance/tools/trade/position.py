#!/usr/bin/env python
#-*- coding:utf-8 -*-


import os
import json


class PositionManager:

    def __init__(self, stgname):
        self.stgname = stgname
        self.prefix = 'postions'
        self.path = f'{self.prefix}/{self.stgname}.json'
        os.makedirs(self.prefix, exist_ok=True)
        if not os.path.exists(self.path):
            with open(self.path, 'w') as fp:
                json.dump({'pos': 0}, fp)

    def load(self, key=None):
        with open(self.path) as fp:
            pos = json.load(fp)
        if not key:
            return pos
        return pos[key]
    
    def save(self, data, key=None):
        if key:
            with open(self.path) as fp:
                pos = json.load(fp)
            pos[key] = data
        else:
            pos = data
        with open(self.path, 'w') as fp:
            json.dump(pos, fp)
        return pos