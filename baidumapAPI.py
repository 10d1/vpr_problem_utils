# -*- coding: utf-8 -*-
"""
Created on Fri Oct 29 11:45:21 2021
Calling baidu API and get a the location information and path then save them as
json file.
@author: Shelley
"""

import json
import os
import sys
import requests
import pandas as pd
import time
import random
import re


def convert_to_float(n):
    if isinstance(n, str):
        num = re.search(r'[-+]?[0-9]+\.[0-9]+', n, 0)[0]
    else:
        num = n
    return float(num)

def formate_coordinate(latitude, longitude):
    lat = convert_to_float(latitude)
    lng = convert_to_float(longitude)
    return "{:.6f},{:.6f}".format(lat, lng)


class BaiduAPIConn(object):
    """
    Use request package to get data from baidu geography code、
    @Attr:
        get_coordinate: get geograph code from baidu API for given address
        get_route_info: get route and save as json for 2 given points
    """
    def __init__(self, ak, output_path):
        """
        @Args:
            ak: ak that for baidu application
            Please view the following url to regist baidu api
            https://lbsyun.baidu.com/apiconsole/key#/home
        """
        self.ak = ak
        self.output_path = output_path

    def get_coordinate(self, id, address):
        """
        Call baidu geograph code api to get coordinate for a given address.
        Please view https://lbsyun.baidu.com/index.php?title=webapi/guide/webservice-geocoding
        for official documents of baidu api
        @args:
            id: Id to indentified with address
            address: chinese address
        """
        url = "https://api.map.baidu.com/geocoding/v3/?address=%s&output=json&ak=%s"
        try:
            req = requests.get(url % (address, self.ak))
            addr_content = req.content.decode(encoding='utf-8')
        except:
            info = sys.exc_info()
            print(info[0], info[1])
            return None
        address_value = json.loads(addr_content)
        print("Save location for %s" % str(id))
        print(address)
        print(addr_content)

        with open(os.path.join(self.output_path, "%s.json" % str(id)), 'w',
                  encoding="utf-8-sig") as rf:
            json.dump(address_value, rf, ensure_ascii=False)

        return address_value


    def get_route_info(self, id, origin, destination):
        """
        Call baidu geograph code api to get coordinate for a given address.
        Please view https://lbsyun.baidu.com/index.php?title=webapi/direction-api-v2
        for official documents of baidu api
        @args:
            id: Id to indentified with address
            origin: latitude, longitude
            destination: latitude, longitude
        """
        url = "https://api.map.baidu.com/direction/v2/driving?origin=%s&destination=%s&type=2&ak=%s"
        try:
            text = url % (formate_coordinate(*origin),
                          formate_coordinate(*destination),
                                      self.ak)
            req = requests.get(text)
            print(text)
            route_content = req.content.decode(encoding='utf-8')
        except:
            info = sys.exc_info()
            print(info[0], info[1])
            return None
        route = json.loads(route_content)
        print("Save location for %s" % str(id))
        print(route_content)

        with open(os.path.join(self.output_path, "%s.json" % str(id)), 'w',
                  encoding="utf-8-sig") as rf:
            json.dump(route, rf, ensure_ascii=False)

        return route


if __name__=='__main__':
    ak = "XEMXArUaUBbFEK1hd9ilOnNXIlIvrlK0"

    # Steps 1 get geo loactions per address
    bd_conn = BaiduAPIConn(ak, "./geocoding")
    data = pd.read_csv("Address.csv", encoding="gbk")

    for i, r in data.iterrows():
        address = bd_conn.get_coordinate(r['ID'], r['City'] + "市" + r['Address'])
        time.sleep(random.random())


    # Step 2 generate loc to loc direcations
    bd_conn = BaiduAPIConn(ak, "./route")
    data = pd.read_csv("Address.csv", encoding="gbk")

    bd_conn = BaiduAPIConn(ak, "./routes")
    conn = pd.read_excel("connection_jn_type3.xlsx")
    conn['Route_ID'] = conn.apply(lambda x: x['ID_orig'] + "-" + x['ID_dest'], axis=1)
    for i, r in conn.iterrows():
        distance = bd_conn.get_route_info(r['Route_ID'],
                                          r['geocoding_orig'].split(","),
                                          r['geocoding_dest'].split(","))
        time.sleep(random.random())

