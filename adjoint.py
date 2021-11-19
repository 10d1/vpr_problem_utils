# -*- coding: utf-8 -*-
"""
Created on Thu Nov 18 15:32:56 2021

@author: Shelley
"""

import pandas as pd
import json


adjoinpro = pd.read_json("adjoin_province.json",  encoding="utf8")

items = []
for i, row in adjoinpro.iterrows():
    name, adjoins = row[['enName','adjoins']]
    try:
       for a in adjoins:
           items.append([name,a.get('enName')])
       print(name, "has %i neibours!" % len(adjoins))
    except:
       print(name, "has no neibours!")

adjoinpro_df = pd.DataFrame(items, columns=['province','adjoint'])
adjoinpro_df.to_excel("adjoin_province.xlsx", index=False)