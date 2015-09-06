import os
import time
from datetime import datetime
import logging
from runSheetMacro import launchExcel
from tools.otherutil import ntmadsubmit, dateoffset, xldate, tuple3d
from tools.dbutil import maddb
from tools.westutil import load_market

import PyWestminster as west
import PyWestRamp as ramp
 
from rampdiff import read_ramp, write_ramp
from pandas import DataFrame, concat
import numpy as np
import pdb


logger = logging.getLogger('')
logger.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
console = logging.StreamHandler()
console.setFormatter(formatter)

logger.addHandler(console)

dstr = datetime.today().strftime("%d%m")
yestdstr = dateoffset(datetime.today(), -1, "%d%m")


def waitforcash():
	cashfile = r"\\sins00120165\Reporting\Risk\rvg\EurOpen\BkLonxHybrids\ActRpt."+dstr
	logger.info("waiting cash....")
	while not os.path.exists(cashfile):
		time.sleep(60*5)
	logger.info("cash arrived")

def intradaysnapshot():
	logger.info("intraday snapshot")
	cmdline = "LON_MM_EVENING_INTRADAY GFTBSGL --force-priority 100 --job MKT_SNAPSHOT_LIVE_FASTINTRA --user-name SG435551 --now  --no-tfc --sub-batch _FAST --ignore-day"
	ntmad_ret = ntmadsubmit(cmdline)
	jobid = ntmad_ret["job_id"]
	mad = maddb("MADBUKL", {"select_progress":"""select job_id, proportion_done, sts_cod from exo_evt_log where job_id in (%s)"""})

	while not mad.isdone(jobid):
		time.sleep(60*5)

	logger.info("intradaysnapshot done")

def spotcorrection():
	tday = dateoffset(datetime.today(), 0)
	rampset = "OSPG TEST 6"
	rampdate = xldate(tday)

	mkt = load_market("mkt", rampset, rampdate, rampdate)
	ccy1ccy2 = [['USD','BRL'], ['USD','JPY'], ['USD','TRY'], ['TRY','JPY'], ['BRL','JPY']]
	df = DataFrame(ccy1ccy2, columns=['CCY1','CCY2'])
	df['Mid'] = df[['CCY1','CCY2']].apply(lambda x: west.FXGetSpot("mkt", x[0], x[1]), axis=1)
	df['SpotDate'] = df[['CCY1','CCY2']].apply(lambda x: west.GetFXSpotDate2(rampdate, x[0], x[1], 'X', False), axis=1)
	df["SpotDate"][3] = west.Add(rampdate,1,"bd",'',"TYO#IST#NYK")
	df['DF1'] = df[['CCY1', 'SpotDate']].apply(lambda x: west.Df(x[1],"mkt",rampdate,'-5','',x[0]), axis=1)
	df['DF2'] = df[['CCY2', 'SpotDate']].apply(lambda x: west.Df(x[1],"mkt",rampdate,'-5','',x[0]), axis=1)
	df['CashRate'] = df['Mid']*df['DF2']/df['DF1']
	df['SpotRate'] = df['CashRate']*df['DF1']/df['DF2']
	#df = df.set_index(['CCY1', 'CCY2'])

	fxspot=[]
	for t in ramp.RampReadCurve("SPOT FX RATES", rampset, rampdate, 2).to_tuple()[0]:
	    if not t[0]+t[1] in ["TRYJPY", "BRLJPY"]:
	        fxspot.append(t)

	fxspot.extend([('TRY', 'JPY',df["SpotRate"][3],df["SpotRate"][3]), ('BRL', 'JPY',df["SpotRate"][4],df["SpotRate"][4])])
	sts = ramp.RampWriteCurve(tuple3d(fxspot), "SPOT FX RATES", rampset, rampdate, 2)
	if sts[:2].upper() != "OK":
		logger.error("SPOT FX contribution failed")

	#correct eurcny vol
	df_eurusd = read_ramp('HYB EURUSD VOL MKT VOLS', rampset, rampdate)
	df_eurusd = df_eurusd.ix[:14]
	df_usdcny = read_ramp('HYB USDCNY VOL MKT VOLS', rampset, rampdate)
	df_eurcny = read_ramp('HYB EURCNY VOL MKT VOLS', rampset, rampdate)

	df_cross = np.sqrt(np.power(df_eurusd["ATM"],2)+np.power(df_usdcny["ATM"],2))
	df_check = np.abs(df_eurcny["ATM"]-df_eurusd["ATM"])>0.5*df_usdcny["ATM"]

	df_eurcny["ATM"] = concat([df_eurcny["ATM"], df_cross, df_check], axis=1).apply(lambda x: x.values[1] if x.values[2] else x.values[0], axis=1)


	df_eurcny = df_eurcny.reset_index()
	curvedata = [["Vols"]+df_eurcny.columns.tolist()]
	curvedata.extend([['']+t for t in df_eurcny.values.tolist()])
	sts = write_ramp(curvedata, 'HYB EURCNY VOL MKT VOLS', rampset, rampdate)
	if sts[:2].upper() != "OK":
		console.error("EURCNY vol contribution failed")



def intradayrun():
	logger.info("run intraday risk batch")
	sheet = r"\\sinemc114042\swaps\OSPG\Skeleton\London\Contribution\RunRiskReports.xls"
	#launchExcel(sheet=sheet,macro="RunAllRisk", toQuit=True)

	filecheckpath = r"\\sins00120165\Reporting\Risk\%s\EURINTRADAY\bkLONXHYBRIDS"
	filecheck = ["PV", "PVNEW", "FxDeltaConsistent", "FxDeltaConsistentNew", "PnlExplain", "PnlExplain253"]

	avail = False
	while not avail:
		for system in ["MAD", "RVG"]:
			files = [f % system for f in [os.path.join(filecheckpath, ".".join([t, yestdstr if "PnlExplain" in t else dstr])) for t in filecheck]]
			avail = sum(map(os.path.exists, files))==len(files)
			if not avail:
				break
		if not avail:
			time.sleep(60)

	logger.info("intraday available")

if __name__ == '__main__':
	waitforcash()
	intradaysnapshot()
	spotcorrection()
	intradayrun()

