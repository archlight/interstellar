import pandas as pd
import PyWestRamp as ramp
from datetime import datetime
from itertools import chain
from io import StringIO
from tools.otherutil import xldate
import numpy as np
from operator import itemgetter
import os
import pdb


def getdf(xlrange):
    return pd.read_csv(StringIO(tuple2str(xlrange)),index_col=0)

def tuple2str(data):
    s=""
    for t in data:
        s+=",".join(map(str, filter(lambda x: not x is None, t)))
        s+="\n"
    return s

def rampdiff(item, baseSet, derivedSet, baseDate, derivedDate):
    base_df = read_ramp(item, baseSet, baseDate)
    df = read_ramp(item, derivedSet, derivedDate)

    #pdb.set_trace()
    diff = df-base_df
    diff=diff[diff!=0].dropna(how="all", axis=1).dropna(how="all", axis=0)
    final = pd.concat([base_df.ix[diff.index, diff.columns], df.ix[diff.index, diff.columns], diff], keys=["base", "derived", "diff"])
    return final

def read_ramp(item, setname, setdate):
    if "VOL MKT VOLS" in item:
        data = ramp.RampReadCurve(item, setname, setdate, 101).to_tuple()[0]
        #pdb.set_trace()
        col = [t[0] for t in data]
        start, end1, end2 = col.index("Vols"), col.index("Params"), col.index("RefFXSpot")
        
        if max([end1,end2])<start:
            return getdf([t[1:] for t in data[start:]]) 
        else:
            return getdf([t[1:] for t in data[start:min([end1, end2])]])
    else:
        return getdf(ramp.RampReadCurve(item, setname, setdate, 101).to_tuple()[0])

def write_ramp(curvedata, item, setname, setdate):
    if "VOL MKT VOLS" in item:
        data = ramp.RampReadCurve(item, setname, setdate, 101).to_tuple()[0]

        col = [t[0] for t in data]
        start, end1, end2 = col.index("Vols"), col.index("Params"), col.index("RefFXSpot")

        curvedata.append(data[end2])
        if end1 > max(start, end2):
            curvedata.extend(data[end1:])
        else:
            curvedata.extend(data[end1:max(start, end2)])

    curvedata = [list(map(lambda x: '' if x is None else x, t)) for t in curvedata]
    return ramp.RampWriteCurve(curvedata, item, setname, setdate, 2)   

def test_rampdiff(baseSet, baseDate, derivedSet, derivedDate, itemtypes=["FX WING VOL","FX VOL MARKET VOLS", "Generic Correlation Curve"]):
    """
    @param baseSet --London Close
    @param baseDate --T-2
    @param derivedSet --OSPG TEST 3
    @param derivedDate --T-2
    """
    changedlist=[]
    for x in itemtypes:
        if len(ramp.RampFindItems(derivedSet, derivedDate, x, "",1).to_tuple()):
            changedlist.extend([t[0] for t in ramp.RampFindItems(derivedSet, derivedDate, x, "",1).to_tuple()[0]])
     
    json = {}            
    for item in changedlist:
        if not "FXO" in item:
            df = rampdiff(item, baseSet, derivedSet, baseDate, derivedDate)
            #df = df.reset_index()
            json[item] = [df.ix["diff"].T.to_json()]
    return json
        
if __name__ == '__main__':
    if len(os.sys.argv)==4:
        baseSet, derivedSet, dstr=os.sys.argv[1:]
        t = xldate(datetime.strptime(dstr, '%d/%m/%Y'))
        
        d = test_rampdiff(baseSet, t, derivedSet, t)
        print(d)