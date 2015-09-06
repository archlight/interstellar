import tornado.httpserver
import tornado.ioloop
import tornado.options
import tornado.web
import tornado.websocket
from tornado import web, gen
from tornado.options import define, options
from tornado.escape import json_encode
from tools.dbutil import maddb, mongodb
from tools.westutil import write_cmitem
from tools.ThreadPool import ThreadPool
from tools.otherutil import dateoffset, xldate, trunc
from ntmadservice import *
from PriceChangeSnapshot import PriceChangeLive
from rampdiff import test_rampdiff
from datetime import datetime, timedelta
import json
import time
import os
import pdb

logger = logging.getLogger('')
logger.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
fh = logging.FileHandler(r'\\SINEMC114042\risktech\Tools\IRG\Log\restfultest.log')
fh.setFormatter(formatter)
console = logging.StreamHandler()
console.setFormatter(formatter)

logger.addHandler(console)


class BaseHandler(tornado.web.RequestHandler):
    @property
    def mongo(self):
        return self.application.mongo

class RampDiff(BaseHandler):
    def post(self):
        try:
            baseSet = self.get_argument("baseSet")
            destSet = self.get_argument("destSet")
            setDate = self.get_argument("setDate")
            t = xldate(datetime.strptime(setDate, '%d/%m/%Y'))
            self.set_header('Content-Type', 'application/json')
            self.write(json_encode(test_rampdiff(baseSet, t, destSet, t)))
        except Exception as e:
            self.write(e)

    def get(self):
        pass

class RebuildIndex(BaseHandler):

    def post(self):
        self.reglib = list(self.mongo.meteor.errtemplate.find({},{"_id":0}))
        self.mongo.rebuildIndex(self.reglib, buildall=True)
        print("rebuild complete")
        self.write("OK")

    def get(self):
        pass

class runriskHander(BaseHandler):
    
    def post(self):
        try:
            t_now = datetime.now()
            activity= self.mongo

            body = str(self.request.body)
            request = json.loads("{"+body[3:-2]+"}")
            logger.info(request)
                        
            session_id = request["user-name"] + "_" + t_now.strftime("%H%M%S")

            tornado.ioloop.IOLoop.instance().add_callback(self.ntmadcallback, session_id, request)
            self.write("%s" % (session_id))
        except Exception as e:
            logger.info("session ended in error %s" % e)
            activity.end_session("Error", datetime.now(), session_id)
            self.write("NOK")

    @gen.coroutine
    def ntmadcallback(self, session_id, request):

        try:
            logger.info("callback started for %s" % session_id)

            cmd = ntmadcmd(session_id, request)

            logger.info(cmd.depcmds)
            logger.info(cmd.cmds)

            logger.info("session initiated %s" % session_id)
            self.mongo.start_session(session_id, request, cmd.db)

            if len(cmd.depcmds):
                tornado.ioloop.IOLoop.instance().add_callback(self.ntmadtask, cmd, True)
            else:
                if len(cmd.fx2d):
                    x, y = cmd.fx2d
                    if not "X" in x:
                        x, y = y, x
                    xccy = x.split(".")[-1]
                    xccy = xccy[:3]+"/"+xccy[3:]
                    yccy = y.split(".")[-1]
                    yccy = yccy[:3]+"/"+yccy[3:]
                    sts = write_cmitem([xccy] + request[x].split(","), "Cedar.Public.Singapore Pilot.Ranges.FX2DMATRIX xAxis")
                    sts = sts and write_cmitem([yccy] + request[y].split(","), "Cedar.Public.Singapore Pilot.Ranges.FX2DMATRIX yAxis")


                tornado.ioloop.IOLoop.instance().add_callback(self.ntmadtask, cmd, False)

            logger.info("callback ended for %s" % session_id)
        except Exception as e:
            logger.error("%s ended in error %s" % (session_id, e))
            self.mongo.end_session("Error", session_id)          

    @gen.coroutine
    def ntmadtask(self, cmd, dep):
        try:
            ntmad_ret = cmd.submit(dep)
            logger.info(ntmad_ret)
            self.mongo.insert_jobs(cmd.session_id, ntmad_ret)
            while not self.mongo.is_done(ntmad_ret["job_id"]):
                yield gen.Task(tornado.ioloop.IOLoop.instance().add_timeout, time.time()+1)
            if dep:
                tornado.ioloop.IOLoop.instance().add_callback(self.ntmadtask, cmd, False)
            else:
                self.mongo.end_session("Done", cmd.session_id)
                logger.info("session id %s ended" % cmd.session_id)
        except Exception as e:
            logger.error("%s ended in error %s" % (session_id, e))
            self.mongo.end_session("Error", session_id) 

class queryjobsHandler(BaseHandler):
    def get(self):
        session_id = self.get_argument("session_id")
        response = self.mongo.query_session(session_id, self.application.sysdate)
        logger.info(response)
        self.write(json_encode(response))

class MainHandler(BaseHandler):
    def get(self):
        self.write("Web Service for interstellar")


class Application(tornado.web.Application):

    def __init__(self):
        handlers = [
                (r"/", MainHandler),
                (r"/interstellar/rampdiff", RampDiff),
                (r"/interstellar/rebuildindex", RebuildIndex),
                (r"/ntmadservice/runrisk", runriskHander),
                (r"/ntmadservice/queryjob", queryjobsHandler)
        ]
        settings = dict(debug=True)
        tornado.web.Application.__init__(self, handlers, **settings)

        self.menus = json.load(open("menuConfig.json"))
        self.menus_mtime = os.path.getmtime(os.path.abspath("menuConfig.json"))
        self.mad = maddb(json.load(open("madQuery.json")))
        self.mongo = mongodb('mongodb://localhost:3001/', self.mad)
        self.sysdate = datetime.today()
        self.reglib = list(self.mongo.meteor.errtemplate.find({},{"_id":0}))

    def rollsysdate(self):
    	logger.info("system rolled")
    	self.sysdate = datetime.today()
    	tornado.ioloop.IOLoop.instance().add_timeout(timedelta(seconds=24*60*60), self.rollsysdate)

    def rrqueueRefresh(self):
        self.mongo.updateProgress(self.sysdate)


    def jobqueueRefresh(self, inception=False):
        mtime = os.path.getmtime(os.path.abspath("menuConfig.json"))
        if self.menus_mtime > mtime:
            self.menus = json.load(open("menuConfig.json"))
            self.menus_mtime = mtime

        baseDt = dateoffset(self.sysdate, -1,"%d/%m/%Y")
        for loc, v in self.menus.items():
            farm = v["mad"]
            for scene, vv in v["scenes"].items():
                for batch, jobs in vv["monitor"].items():
                    self.mongo.refreshQueue(farm, baseDt, batch, jobs, scene, inception)


        self.mongo.rebuildIndex(self.reglib)

    def livefeed(self):
        logger.info("PriceChangeLive")
        df = PriceChangeLive()
        self.mongo.updateLiveFeed(json.loads(df.to_json(orient="records")))


if __name__ == "__main__":
    app = Application()
    http_server = tornado.httpserver.HTTPServer(app)
    http_server.listen(8080)
    #app.listen(443)

    delta = trunc(dateoffset(app.sysdate, 1))-app.sysdate
    tornado.ioloop.IOLoop.instance().add_timeout(timedelta(seconds=delta.seconds+7*60*60), app.rollsysdate)
    app.jobqueueRefresh(True)
    tornado.ioloop.PeriodicCallback(app.jobqueueRefresh, 5*1000*60).start()
    app.livefeed()
    tornado.ioloop.PeriodicCallback(app.livefeed, 1*1000*60).start()
    tornado.ioloop.PeriodicCallback(app.rrqueueRefresh, 1000*1).start()
    logger.info("interstellar started")
    tornado.ioloop.IOLoop.instance().start()
    
