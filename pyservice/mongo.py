from tools.dbutil import maddb, mongodb
from datetime import datetime,timedelta
from pymongo import MongoClient
from pandas import DataFrame
from tools.westutil import *
import json
import time

menuTemplate = {
    "location": 'Tokyo',
    "snapshots": [
      {
        "name": 'jpyclose',
        "eta": '7:30',
        "risk": {
            "pv":100,
            "fxdelta":[
                {"ccypair":"USDJPY", "number":200},
                {"ccypair":"EURJPY", "number":200}
            ]
        }
      }
    ]
  }

meteor = MongoClient('mongodb://localhost:3001/').meteor

def jobqueueRefresh():
    menus = json.load(open("menuConfig.json"))
    sql = json.load(open("madQuery.json"))

    mad = maddb(sql)
    mongo = mongodb('mongodb://localhost:3001/')

    baseDt = datetime.strftime(datetime.today()-timedelta(days=1), "%d/%m/%Y")
    for loc, v in menus.items():
        for farm, batches in v["monitor"].items():
            if "MAD" in farm:
                for batch, jobs in batches.items():
                    if len(jobs):
                        df = mad.progress_by_jobs(farm, baseDt, batch, ",".join(map(lambda x: "'%s'" % x, jobs)))
                        mongo.jobqueueUpdate(df)
                    else:
                        df = mad.progress_by_batch(farm, baseDt, batch)
                        mongo.jobqueueUpdate(df)

def populate(filename):
    meteor.errtemplate.remove()
    meteor.errtemplate.insert(json.load(open(filename)))

def test():
    d = meteor.errors.find({"JOB_ID":{"$in":[12,43]},
        "CFMN_NO":{"$in":[12,43]}})
    print(list(d))
    if d:
        print("OK")
    if len(list(d)):
        print("NOK")

def dumpjson():
    df = read_cmitem(".".join(["IRLP Config.Singapore.RW.NTMADService", "RISKGROUP"]))
    grouped = df.groupby(["GROUP", "BATCH"])
    from collections import defaultdict

    results = defaultdict(lambda: defaultdict(dict))

    for index, value in grouped:
        for i, key in enumerate(index):
            if i == 0:
                nested = results[key]
            elif i == len(index) - 1:
                d = {}
                d["JOBS"]=[]
                for i, idx in enumerate(value.index):
                    if i == 0:
                        d["BOOK"] = value["BOOK"].ix[idx]
                        d["DAYOFFSET"] = "0" if value["DAYOFFSET"].ix[idx]=="" else str(value["DAYOFFSET"].ix[idx])
                        d["GARDEN"] = value["GARDEN"].ix[idx]
                        d["TIMINGCALC"] = value["TIMINGCALC"].ix[idx]
                        d["PRIORITY"] = str(value["PRIORITY"].ix[idx])
                    d["JOBS"].append({"JOBNAME":value["JOBNAME"].ix[idx],"RISKFILE":value["RISKFILE"].ix[idx]})

                nested[key] = d
            else:
                nested = nested[key]
    #print(results)
    json.dump(results, open("RISKGROUP.json","w"), indent=4)



if __name__ == "__main__":
    #jobqueueRefresh()
    #populate("errtemplate.json")
    dumpjson()
