import os
import sys
import socket
import time
import logging
import pprint
from datetime import datetime
from collections import defaultdict, namedtuple
from queue import Queue

from tools.dbutil import maddb, mongodb
from tools.otherutil import dateoffset, simplemail, ntmadsubmit

import pdb

import json

from pandas import DataFrame, concat

logger = logging.getLogger(__name__)
                                                                                                               
class ntmadcmd():
    dbmapping = {"SINGAPORE":"GFTBSGL", "TOKYO":"GFTBSGL", "LONDON":"MADBUKL"}

    def __init__(self, session_id, request):
        self.riskconfig = json.load(open("RISKGROUP.json"))
        self.session_id = session_id
        self.request = request        
        self.basedate = datetime.strptime(request["base-date"], "%d%m%Y")
        if "dboverride" in self.request:
            self.db = self.request["dboverride"]
        else:
            self.db = self.dbmapping[request["location"]] if "location" in request else "GFTBSGL"
        
        self.overrides = []
        for t in json.load(open("extraoverrides.json")):
            if t["TAG"] in request and request[t["TAG"]]=="Y":
                 self.overrides.append(t["VAL"])

       
        
        groupindex=defaultdict(list)
        for k, v in request.items():
            if k.startswith("job"):
                t = v.split(".")
                groupindex[t[0]].append(t[1] if len(t)>1 else "All")

        logger.info(groupindex)
        self.mapping = {}
        self.depcmds = self.depcmds()
        self.cmds = self.buildcmd(groupindex)

        self.fx2d = [t for t in self.request.keys() if t.startswith("FX2D")]
    
    def submit(self, dep=False):
        return ntmadsubmit(self.depcmds) if dep else ntmadsubmit(self.cmds)

    def depcmds(self):
        cmds = []
        if "REFREEZE" in  self.request and self.request["REFREEZE"]=="Y":
            cmd = self.buildcmd({"REFREEZE":["All"]})
            cmds.extend([t + " --add-co MCEB_INFO C --add-co MCEB_INFO_SETNO 83621" for t in cmd])

        if "runTiming" in  self.request and self.request["runTiming"]=="Y":
            cmd = self.buildcmd({"PVTiming":["All"]})
            cmds.extend(cmd)

        return cmds
    
    def buildcmd(self, groupindex):
        cmds = []
        for g, batches in self.riskconfig.items():
            if g in groupindex.keys():
                for batch, v in batches.items():
                    jobs = filter(lambda x: x[0]!="*" and (x[0] in groupindex[g] or groupindex[g][0]=="All"), [(t["JOBNAME"],t["RISKFILE"]) for t in v["JOBS"]])
                    jobs = list(jobs)
                    self.mapping.update(dict(jobs))
                    cmd ='"%s" %s %s' % (batch, self.db, " ".join(map(lambda x: '--job "%s"' % x[0], jobs)))
                    timingcat = self.request["timing-cat"] if "timing-cat" in self.request else v["TIMINGCALC"]

                    c = ' --base-date %s --sub-book "%s" "%s" --force-farm "%s" --force-priority %s --timing-cat %s ' % (dateoffset(self.basedate, int(v["DAYOFFSET"]), "%d/%m/%Y"), v["BOOK"], self.request["sub-book"], v["GARDEN"], v["PRIORITY"], timingcat)
                    if "force-ramp" in self.request:
                        c = c + ' --force-ramp "%s"' % self.request["force-ramp"]

                    cmd = cmd + c + " ".join(self.overrides)
                    cmd = cmd + " --sub-batch %s" % self.request["sub-batch"]
                    cmd = cmd + " --no-fltr --no-tfc --ignore-day --add-co FORCE_VALID_MODEL FALSE --add-co TARGET_PKT_TM 800"
                    if "eod-fixing" in self.request:
                        cmd = cmd + " --eod-fixing %s" % self.request["eod-fixing"]
                    cmds.append(cmd)

        return cmds
    
    def __iter__(self):
        for t in self.cmds:
            yield t
    
    def debug(self):
        for t in self.depcmds:
            print(t)
        for t in self.cmds:
            print(t)

def test():
    cmd = ntmadcmd('sg908278_12345', {"force-ramp":"london close","runtiming":"N", "base-date":"04022015", "job1":"FXIR", "job2":"FxVega.MultiCcySohoWingsATM","REFREEZE":"Y", "location":"SINGAPORE","sub-book":"MAD DEAL 40104410"})
    cmd.debug()

if __name__ == "__main__":
    test()
        
    
