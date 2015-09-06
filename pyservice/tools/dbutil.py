import pyodbc
from pandas import DataFrame, concat, isnull, notnull
from pandas.io.sql import read_frame
from pymongo import MongoClient
from datetime import datetime
from tools.otherutil import trunc

import re
import json
import pdb

import logging

logger = logging.getLogger('')

class maddb():

    connect_str = "Driver={Oracle dans ORACLE_10g};DBQ=%s;Uid=%s;PWD=%s"
    rootpath={"MADTUKL":r"\\lonshr-madtmptyorpt\madtmptyorpt\TempResults\\madliv\Grass",
              "MADBUKL":r"\\lonshr-mad\MAD\gft1ukl\grass",
              "GFTBSGL":r"\\sinemc114042\MAD\madliv\Grass"}

    def __init__(self, query_templates={}):

        self.query = query_templates
        self.conns={}
        self.cursors={}
        for t in self.logins():
            self.conns[t[0]] = pyodbc.connect(self.connect_str % t)
            self.cursors[t[0]] = self.conns[t[0]].cursor()


    def __getattr__(self, k):
        if k in self.query:
            template = self.query[k]
            return lambda *args: self.select(template, args)

    def select(self, cmd, args):
        dbinstance = args[0]
        q = cmd % args[1:] if len(args)>1 else cmd
        return read_frame(q, self.conns[dbinstance])

    def logins(self):
        return [("MADTUKL","mad", "mad"),
                        ("MADBUKL","mad_ro", "mad_ro"),
                        ("GFTBSGL", "mad_ro", "mad_ro")]

    def riskpath(self, dbinstance):
        return self.rootpath[dbinstance]

class mongodb():

    def __init__(self, url, mad):
        client = MongoClient(url)
        self.meteor = client.meteor
        self.mad = mad

    def start_session(self, session_id,request,maddb):
        doc = {"session_id":session_id, 
               "user":request["user-name"],
               "status":"Running",
               "start_time":datetime.now(),
               "book":request["sub-book"],
               "maddb":maddb}
        self.meteor.activity.insert(doc)

    def end_session(self, status, session_id):
        self.meteor.activity.update({"session_id":session_id}, {"$set":{"status":status, "end_time":datetime.now()}})

    def is_done(self, jobids):
        jobids = list(map(int, jobids))
        
        sts = [t["sts_cod"] for t in self.meteor.rrqueue.find({'job_id':{"$in":jobids}},{"_id":0, "sts_cod":1}) if t["sts_cod"]=="OK"]
        return len(sts) == len(jobids)

    def insert_jobs(self, session_id, ntmad_ret, mapping=None):
        docs = []
        for i, t in enumerate(ntmad_ret["job_id"]):
            docs.append({"session_id":session_id, "job_id":int(t), "job_name":mapping[ntmad_ret["job_name"][i]] if mapping else ntmad_ret["job_name"][i], "progress":0, "sts_cod":"QU"})
        self.meteor.rrqueue.insert(docs)

    def updateProgress(self, sysdate):
        
        for doc in self.meteor.activity.find({"start_time":{"$gt":trunc(sysdate)}, "status":"Running"}):
            dbinstance = doc["maddb"]
            jobids = ",".join(map(lambda x: str(x["job_id"]), self.meteor.rrqueue.find({"session_id":doc["session_id"]},{"_id":0, "job_id":1})))
            if len(jobids):
                df = self.mad.select_progress(dbinstance, jobids)

                df.apply(lambda x: self.meteor.rrqueue.update({"job_id":x.JOB_ID},{"$set":{"sts_cod":x.STS_COD,"progress":x.PROPORTION_DONE}}),axis=1)
        

    def query_session(self, session_id, sysdate):
        username, _ = session_id.split("_")
        summary = [(t["session_id"], t["status"]) for t in self.meteor.activity.find({"start_time":{"$gt":trunc(sysdate)}, "user":username})]
        book = self.meteor.activity.find({"session_id":session_id})[0]["book"]
        jobs = []
        for t in self.meteor.rrqueue.find({"session_id":session_id}, {"_id":0}):
            jobs.append("%d,%s,%.2f" % (t["job_id"], t["job_name"], t["progress"]))

        return {"book":book, "joblist":";".join(jobs)}

    def updateLiveFeed(self, jsondata):
        t_now = datetime.now()
        for doc in jsondata:
            doc["updatetime"] = t_now
            self.meteor.quotes.save(doc)

    def simplify(self, singleRecord, reglib):
        toUpdate = {}

        for t in reglib:
            pattern = t["REGEXPR"]
            errorType = t["TYPE"]
            # if errorType == "Gentoo Variance" and singleRecord["JOB_ID"]==54052:
            #     pdb.set_trace()
            m = re.search(pattern, singleRecord["MESSAGE_TEXT"].replace('\t', ' ').replace('\n', ''))
            if m:
                toUpdate["TYPE"] = errorType
                toUpdate["TAGS"] = list(m.groups())
                break
        if not "TYPE" in toUpdate:
            toUpdate["TYPE"] = "T0"
            toUpdate["TAGS"] = ["other"]
        return toUpdate

    def rebuildIndex(self, reglib, buildall=False):
        if buildall:
            #pdb.set_trace()
            todayerrors = self.meteor.errors.find({"CREATEDAT":{"$gt":datetime.strptime(datetime.strftime(datetime.now(),"%d%m%Y"),"%d%m%Y")}})
        else:
            todayerrors = self.meteor.errors.find({"$or":[{"TYPE":{"$exists":0}}, {"TYPE":"T0"}]})

        for t in todayerrors:
            if t:
                a = self.simplify(t, reglib)
                self.meteor.errors.update({"_id":t["_id"]}, {"$set":{"TYPE":a["TYPE"],"TAGS":a["TAGS"]}})

    def refreshQueue(self, farm, baseDt, batch, jobs, scene, inception=False):
        if len(jobs):
            extraArg = " and j.job_name in (%s)" % ",".join(map(lambda x: "'%s'" % x, jobs))
        else:
            extraArg = ""

        df = self.mad.progress(farm, baseDt, batch, extraArg)
        df["SCENE"] = scene
        # JOB_ID is always unqiue
        df_ex = df.set_index("JOB_ID")

        # if inception:
        #     df_ex = df[df["STS_COD"]!="EX"]
        # else:
        #     df_ex = df[df["STS_COD"]=="EX"]

        if len(df_ex):
            self.jobqueueUpdate(df_ex)
            df_ex_errors = self.mad.errors(farm, ",".join(map(lambda x: str(int(x)), df_ex.index)))
            self.errorUpdate(df_ex_errors)

    def selectForUpdate(self, df):
        d = self.meteor.jobqueue.find({"JOB_ID":{"$in":df.index.values.tolist()}}, {"_id":1, "JOB_ID":1, "STS_COD":1})
        dupdate = list(d)

        if len(dupdate):
            df = df.reset_index()
            df = df.drop_duplicates("JOB_ID").set_index("JOB_ID")
            dfa = concat([DataFrame(dupdate).drop_duplicates("JOB_ID").set_index("JOB_ID"), df], axis=1)
            dfupdate = dfa[notnull(dfa["_id"])]
            #dfupdate = dfupdate.reset_index()

            dft = dfupdate["STS_COD"][[0]]!=dfupdate["STS_COD"][[1]]
            idx = dft[dft["STS_COD"]].index

            dft = dfupdate["STS_COD"][[1]]=="EX"
            idx = idx.append(dft[dft["STS_COD"]].index)

            return dfa[isnull(dfa["_id"])][df.columns], dfupdate.reindex(idx)
        else:
            return df, DataFrame()


    def selectForErrorUpdate(self, df):
        d = self.meteor.errors.find({"JOB_ID":{"$in":df["JOB_ID"].unique().tolist()},
                                    "CFMN_NO":{"$in":df["CFMN_NO"].unique().tolist()}}, 
                                    {"_id":0, "JOB_ID":1, "CFMN_NO":1})

        df = df.groupby(["JOB_ID", "CFMN_NO"])[["MESSAGE_TEXT"]].apply(sum)
        
        dlist = list(d)
        if len(dlist):
            df_filter = DataFrame(dlist, columns=["JOB_ID","CFMN_NO"])
            #pdb.set_trace()
            df_filter = df_filter.groupby(["JOB_ID","CFMN_NO"]).apply(len)
            #print(df_filter.index)
            df = df.reindex(df.index - df_filter.index)


        df = df.reset_index()
        return df

    def jobqueueUpdate(self, df):
        #only update EX jobs
        dfnew, dfupdate = self.selectForUpdate(df)

        logger.info(dfnew.head())
        logger.info("-"*50)
        logger.info(dfupdate.head())
        
        if len(dfupdate):
            dfupdate["BASE_DT"] = dfupdate["BASE_DT"].astype(datetime)
            dfupdate.apply(lambda x: self.meteor.jobqueue.update({"_id":x._id},{"$set":{"STS_COD":x["STS_COD"].ix[1],"PROPORTION_DONE":x.PROPORTION_DONE,"BASE_DT":x.BASE_DT,"SCENE":x.SCENE}}, upsert=True),axis=1)
        
        if len(dfnew):
            self.jobqueueNew(dfnew)

    def jobqueueNew(self, df):
        df = df.reset_index()
        df = df.dropna(axis=1, how="all")
        for doc in json.loads(df.to_json(orient="records", date_format="iso")):
            doc["BASE_DT"]=datetime.strptime(doc["BASE_DT"][:10], "%Y-%m-%d")
            doc["ERRCNT"] = 0
            self.meteor.jobqueue.save(doc)

    def errorUpdate(self, df):

        df = self.selectForErrorUpdate(df)

        for doc in json.loads(df.to_json(orient="records")):
            doc["CREATEDAT"] = datetime.today()
            self.meteor.errors.save(doc)

            #pdb.set_trace()
            self.meteor.jobqueue.update({"JOB_ID":doc["JOB_ID"]}, {"$set":{"ERRCNT":self.meteor.errors.find({"JOB_ID":doc["JOB_ID"]}).count()}})

        # df.apply(lambda x: self.meteor.errors.update({"JOB_ID":x.JOB_ID,"CFMN_NO":{"$ne":x.CFMN_NO}},
        #                                             {"$set":{
        #                                             "JOB_ID":x.JOB_ID,
        #                                             "CFMN_NO":x.CFMN_NO,
        #                                             "MESSAGE_TEXT":x.MESSAGE_TEXT,
        #                                             "CREATEDAT":datetime.today()}},
        #                                             upsert=True) ,axis=1)
