# -*- coding: utf-8 -*-
"""
Created on Fri Oct 29 16:41:47 2021
Generate a d2d matrix (upper traingle) and to input to baidu API.
Since the tail version of API has limited of request per day.
We also try to reduce the number of d2d connection by the following styeps.

1) If necessay manully pick the dealer that for the facing PDC, if analysis is limited to 
a single PDC. This step could also be achieved via a prepercessing step.
2) Call baidumapAPI.get_coordinate() to get the geography code for dealer address.
3) Calculate euclidean distance for the following connection:
    a) PDC to all known dealers
    b) Dealer to Dealer route for all dealer that from same province.
4） Clustering the dealers that has really shorter distance as a group 
5) Regenrate the matrix from the grouped dealer
@author: Shelley
"""

import pandas as pd
import json
import os
import numpy as np

from scipy.sparse import csr_matrix
from scipy.sparse.csgraph import connected_components


def get_geocode_from_file(file):
    """
    Read json file that return from baidu, and read atitude, longitude
    code.
    @Args: json file name
    @Returns: (latitude, longitude)
    """
    try:
        with open(file, 'r', encoding="utf-8-sig") as rf:
            geo = json.load(rf)
        return (geo.get("result").get("location").get("lat"),
                geo.get("result").get("location").get("lng"))
    except:
        return "NotFound！"


def __geo_distance(p1, p2):
    """
    Calculate the distance in 2 given geography location:
    Only works for Asha area since we don't try to identified northern
    hemisphere by and - before latitude
    
    """
    rate = np.pi / 180
    r = 6371.004 # Average radius of earth in KM
    lat_1, lon_1 = np.array(p1) * rate
    lat_2, lon_2  = np.array(p2) * rate

    c = np.sin(lat_1) * np.sin(lat_2) + np.cos(lat_1) * np.cos(lat_2) * np.cos(lon_1-lon_2)
    return r * np.arccos(c)


def generate_connections(data, groupby=None):
    """
    Generate a data frame that each row stands for a connection that need
    to be searched on baidu API for actual distance.
    Notice the matrix is asymmetry since we don't want to search a connection 
    twice due to the limitation of API visits. Sinceh the data is just used for 
    cost esitmiations, it doesn't required to be accurate. If the direction of 
    return is required. We could use the same value.

    The connection includes 2 kinds of relations:
    Type=1 starting points to all other points
    Type=2 full mesh connections between all the type 2 data
    
    @Args:
        data: a pandas dataframe the contains required columns:
                [Type, ID, groupby]
        groupby: a list that contains the column names that used for group by.
    @Return:
        conn: a pandas dataframe that each row stands for a connection between a 
        given starting point and ending point.
        And the in all type 2 data, the 2 point are sorted as to make sure the 
        ID of starting points is greater than ending point.
    """
    data = data.copy()
    if "Type" not in data.columns:
        data["Type"] = 2 
        # if no Type colume is givin , set all type to 2 as to generate a
        # full mesh connection between all given points

    if groupby is None:
        groupby = ["groupkey"]
        data["groupkey"] = 1
        # If no group by key is given, generate connection between all given points

    type1_data = data[data['Type']==1][["ID"] + groupby] # only allow for departure
    type2_data = data[data['Type']!=1][["ID"] + groupby] # Allow connection from both way

    # Generate connection from all starting points
    type1_data["Key"] = True
    type2_data["Key"] = True
    oneway_conn =pd.merge(type1_data,
                          type2_data,
                          on='Key',
                          suffixes=['_orig', '_dest']) 
    oneway_conn['Type'] = 1

    # p2p connection from all known point within given groups
    full_conn = pd.merge(type2_data,
                         type2_data,
                         on=groupby,
                         suffixes=['_orig', '_dest'])
    
    full_conn['Key'] = full_conn['ID_orig'] > full_conn['ID_dest']
    full_conn = full_conn[full_conn.Key]
    full_conn['Type'] = 2

    conn = pd.concat([full_conn[['ID_orig', 'ID_dest', 'Type']],
                      oneway_conn[['ID_orig', 'ID_dest','Type']]],
                      axis=0)
    return conn


def calculate_direct_distance(data, sourcepath):
    """
    Fetch geography code from source path and calculate direct distance for all
    p2p connection in given dataframe:
    
    @Args：
        data: a pandas dataframe that contains ID_orig and ID_dest that can be 
        found in the source path.
        sourcepath: a directory that has all geography code saved as json.
            the geography code could be fetched via baidumapAPI get_coordinate()
            method.
    @Returns:
        a pandas data frame with 3 new columns:
            geocoding_orig: starting point (latitude, longitude)
            geocoding_dest: ending point (latitude, longitude)
            geo_distance: The direct distance
    """
    connections =  data.copy()
    geocoding_orig = []
    geocoding_dest = []
    # Compute euclidean distance for the given connections
    for i, row in connections.iterrows():
        geocoding_orig.append(get_geocode_from_file(
                os.path.join(sourcepath,"%s.json" % row['ID_orig'])))
        geocoding_dest.append(get_geocode_from_file(
                os.path.join(sourcepath,"%s.json" % row['ID_dest'])))
    connections['geocoding_orig'] = geocoding_orig
    connections['geocoding_dest'] = geocoding_dest
    connections['geo_distance'] = connections.apply(lambda x:
                                          __geo_distance(x["geocoding_orig"],
                                                         x["geocoding_dest"]),
                                                    axis=1)
    return connections


def conn_matrix(data):
    """
    generate a connection matrix and with given data.
    Since we only as a one-way connection data frame, the conncetion matrix
    has to be completed and symmetry. also the vertix id need to be sorted.
    @Args:
        a pandas dataframe that bears connections.
        Mandatory columns: ID_orig ID_dest
    @Retruns:
        matrix: pandas data bears connection
    """
    data2 = data.copy()
    data2[["ID_orig", "ID_dest"]] = data[["ID_dest", "ID_orig"]] # Switch start and end
    full_data = pd.concat([data, data2])
    full_data['conn'] = 1
    matrix = (full_data.sort_values(["ID_orig", "ID_dest"])
                       .pivot_table(index="ID_orig",
                                    columns="ID_dest",
                                    values="conn",
                                    fill_value=0))
    return matrix


def get_cluster_id(data):
    """
    Split the connection matrix to subgraph and use the lowerset id in the
    subgrap as group id
    """
    graph = csr_matrix(data.values)
    n_components, labels = connected_components(csgraph=graph,
                                                directed=False,
                                                return_labels=True)
    cluster = pd.DataFrame(nb_matrix.index.values, columns=['ID'])
    cluster['Cluster_Lablel'] = labels
    cluster_name = cluster.groupby('Cluster_Lablel').agg({"ID":"min"}).reset_index()
    cluster = pd.merge(cluster,
                       cluster_name,
                       on="Cluster_Lablel",
                       suffixes=['','Cluster'])
    return cluster



if __name__=='__main__':
    json_path = "./geocoding"
    address = pd.read_csv("JN_Address.csv")
    address['Type'] = (address['Type']!="PDC") + 1
    connections = generate_connections(address, groupby=["Province"])
    distances = calculate_direct_distance(connections, json_path)
    distances['geo_distance'].hist(bins=50)
    distances[distances['geo_distance']<=10].hist()

    # We set the boundary of clustering neibours to 2km from the 1 histgram.
    # which mean all dealers that within 2 km are always deiver together
    # The boundary could also be adjusted
    neibours = distances[distances['geo_distance']<=2]
    nb_matrix = conn_matrix(neibours)
    cluster = get_cluster_id(nb_matrix)
    cluster.to_excel("dealer_cluster.xlsx", index=False)

    # Create a new address that merge some neibours toghter so as to reduce the
    # size of p2p connection table
    merged_address = pd.merge(address, cluster, on="ID", how='left')
    merged_address['IDCluster'] = merged_address.apply(lambda x:
                                                   x['ID'] if x['IDCluster'] is
                                                   np.NaN else x['IDCluster'], axis=1)
    merged_address = merged_address[["IDCluster","Type","Province"]].rename(columns = {"IDCluster": "ID"}).drop_duplicates()
    connections_merged = generate_connections(merged_address, groupby=["Province"])
    distances_merged = calculate_direct_distance(connections, json_path)
