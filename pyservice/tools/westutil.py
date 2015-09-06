import PyWestRamp as ramp
import PyWestminster as west
import PyFPGTools as fpg
import PyWestCfgMgr as cfg
from pandas import DataFrame

from tools.otherutil import tuple3d


def load_market(mktname, rampset, rampdate, calcdate):
    params = (('*MESAMARKET', 'LAZYSTRIPPING', 'Y'),
              ('*MESAMARKET', 'LAZYLOADCURVES', 'Y'),
              ('*MESAMARKET', 'LOADCURVEMODE', 'LAZY'))
    
    markets = (('MESA MARKET',),
    	       ('SPOT FX RATES',))

    return ramp.LoadMarketRamp(mktname, tuple3d(markets), rampset, rampdate, calcdate, tuple3d(params)).to_tuple()[0][0][0]

def read_cmitem(cmpath, header=True):
	data = cfg.CMReadItem(cmpath).to_tuple()[0]
	d = [list(map(lambda x: '' if not x else x, t)) for t in data]
	if header:
		return DataFrame(d[1:], columns=d[0])
	else:
		return DataFrame(d)

def write_cmitem(data, cmpath):
	try:
		sts = cfg.CMWriteItem(tuple3d(data), cmpath)
		return sts[:2]=="OK"
	except:
		return True


def Swap(ActStart, MatDate, FixFrq, FixBasis, Mkt, RefCode, SwapType='', RefCode2='', CSAId=-1):
	return west.Swap(ActStart, MatDate, FixFrq, FixBasis, Mkt, RefCode, SwapType,'','',RefCode2,'','','','',0.0,'','','',str(CSAId)).to_tuple()[0][0][0]

def GetSpotDate(tdate, ccy):
	return west.GetSpot(tdate, ccy)

def TenorDate(dt, Tenor, EndRule):
	return west.TenorDate(dt, Tenor, EndRule)

def GetFxSpot(mkt, ccycpl):
	return west.FXGetSpot(mkt, ccycpl[:3], ccycpl[3:])
