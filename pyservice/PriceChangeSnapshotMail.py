import os
from tools.otherutil import xldate, dateoffset, sendemail
from tools.westutil import *
from datetime import datetime, timedelta
import time
from pandas import DataFrame, concat
import pdb

import logging

logger = logging.getLogger('')
logger.setLevel(logging.INFO)
fh = logging.FileHandler(r'\\SINEMC114042\risktech\Tools\IRG\Log\PriceChangeSnapshot.log')
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
fh.setFormatter(formatter)
logger.addHandler(fh)

#FixFrq, FixBasis, Mkt, RefCode, SwapType='', RefCode2='', CSAId=-1

ratechart=[
('Quote', 'QuoteType', 'FixFrq', 'FixBasis', 'RefCode', 'SwapType', 'RefCode2', 'CSAId'),
('USDJPY', 'FXSPOT', '', '', '', '', '', ''),
('USD5Y', 'SWAPRATE', 'S', 'BB', 'UTIBO3', '', '', -1),
('USD5Y30Y', 'SWAPRATE', 'S', 'BB', 'UTIBO3', '', '', -1),
('AUDCRM', 'CRMRATE', 'S', 'A5', 'ABBIL6', '', '', -1),
('JPYXCCY1Y', 'SWAPRATE', 'S', 'BB', 'YLIBO3', 'XBMTM', 'UTIBO3', -5)
]

def getRate(x, mkt, calcdate):
	if x.QuoteType=='FXSPOT':
		return GetFxSpot(mkt, x.Quote)
	elif x.QuoteType == 'SWAPRATE':
		spotdate = GetSpotDate(calcdate, x.Quote[:3])
		tenors = x.Quote[7 if 'XCCY' in x.Quote else 3:].split('Y')[:-1]
		if len(tenors)==1:
			return Swap(spotdate, TenorDate(spotdate, tenors[0]+"Y", 'none'), x.FixFrq, x.FixBasis, mkt, x.RefCode, x.SwapType, x.RefCode2, x.CSAId)
		elif len(tenors)==2:
			return Swap(spotdate, TenorDate(spotdate, tenors[1]+"Y", 'none'), x.FixFrq, x.FixBasis, mkt, x.RefCode, x.SwapType, x.RefCode2, x.CSAId) - Swap(spotdate, TenorDate(spotdate, tenors[0]+"Y", 'none'), x.FixFrq, x.FixBasis, mkt, x.RefCode, x.SwapType, x.RefCode2, x.CSAId)
		elif len(tenors)==3:
			left = Swap(spotdate, TenorDate(spotdate, tenors[0]+"Y", 'none'), x.FixFrq, x.FixBasis, mkt, x.RefCode, x.SwapType, x.RefCode2, x.CSAId)
			mid = Swap(spotdate, TenorDate(spotdate, tenors[1]+"Y", 'none'), x.FixFrq, x.FixBasis, mkt, x.RefCode, x.SwapType, x.RefCode2, x.CSAId)
			right = Swap(spotdate, TenorDate(spotdate, tenors[2]+"Y", 'none'), x.FixFrq, x.FixBasis, mkt, x.RefCode, x.SwapType, x.RefCode2, x.CSAId)
			return 2*mid - left-right
	elif x.QuoteType == 'CRMRATE':
		crm = [
			('Tenor', 'Weight'),
			('1Y', 0.25),
			('2Y', -0.5),
			('3Y', 0.25),
			('5Y', 1.1),
			('7Y', -0.65),
			('10Y', -3.1),
			('15Y', 3.3),
			('20Y', -0.65)
		]
		df_crm = DataFrame(crm[1:], columns=crm[0])
		df_crm['Quote'] = x.Quote[:3] + df_crm['Tenor']
		df_crm['QuoteType'] = 'SWAPRATE'
		df_crm['FixFrq'] = x.FixFrq
		df_crm['FixBasis'] = x.FixBasis
		df_crm['RefCode'] = x.RefCode
		df_crm['SwapType'] = x.SwapType
		df_crm['RefCode2'] = x.RefCode2
		df_crm['CSAId'] = x.CSAId
		s = df_crm.apply(getRate, axis=1, args=(mkt, calcdate))
		return (df_crm['Weight']*s).sum()
	elif x.QuoteType == 'FWDSWAPRATE':
		spotdate = GetSpotDate(calcdate, x.Quote[:3])
		tenors = x.Quote[7 if 'XCCY' in x.Quote else 3:].split('Y')[:-1]
		maturity = int(tenors[0])+int(tenors[1])
		return Swap(TenorDate(spotdate, tenors[0]+"Y", 'none'), TenorDate(spotdate, str(maturity)+"Y", 'none'), x.FixFrq, x.FixBasis, mkt, x.RefCode, x.SwapType, x.RefCode2, x.CSAId)


def calcOfficial(df, tday):
	calcdate = xldate(dateoffset(tday,-1))
	mkt = load_market('mesaofficial', 'OFFICIAL', calcdate, calcdate)
	return DataFrame({"OFFICIAL":df.apply(getRate, axis=1, args=(mkt, calcdate))})

def calcLIVE(df):
	calcdate = xldate(datetime.today())
	mkt = load_market('mesaofficial', 'LIVE', 0, calcdate)
	return DataFrame({"LIVE":df.apply(getRate, axis=1, args=(mkt, calcdate))})

def reporthtml(df, ts):
	template="""
		<html>
		<head>
		  <title></title>
		  <style type="text/css">
		    table {
		    	border-width: 1px;
		    	border-color: #B0B0B0;
		    	border-collapse: collapse; 
		    	border-spacing: 0;
		    }

		    table thead{
		    	padding: 0px
		    }
		    table tbody{
		    	padding: 0px
		    }
		    table th,
		    td
		    {
		    font-size: 12px;    
		    padding-left: 20px;
		    text-align:right
		    }

		    tr td {
		      border-left: 1px solid #B0B0B0;
		      border-right: 1px solid #B0B0B0;
		    }
		    tr td.negative {
		      color: #FF0000
		    }
		    tr td.divider {
		      border-bottom: 1px solid #B0B0B0
		    }
		    tr td:first-child {background-color: #99CCFF}
		    tr th {
		      border: 1px soild #B0B0B0;
		      background-color: #B0B0B0
		    }
		    tr th:first-child {
		      background-color: #18FF3F
		    }
		  </style>
		</head>
		<body>
		<table>
		  <thead>
		    <tr>
		    %s
		    </tr>
		  </thead>
		  <tbody>
		    %s
		  </tbody>
		</table>
		</body>
		</html>
	"""
	bottom_idx = [7, 11, 18, 21, 24, 28, 30]

	th = '<th style="background-color:#00FF00">%s</th>' % ts
	th = th + "".join(map(lambda x: "<th>%s</th>" % x, df.columns[1:]))
	trs = ""
	def formatnumber(num, i):
		try:
			num = float(num)
		except:
			return num
		if i<=7:
			return "%.4f" % float(num)
		else:
			return "%.3f%s" % (float(num)*100,"%")

	for i, row in enumerate(df.values):
		css_class = 'class="divider"' if i in bottom_idx else ""
		tr = '<tr><td style="background-color:#99CCFF; font-weight:bold; text-align:center" %s>%s</td>' % (css_class, row[0])
		if i>7:
			tr = tr + "".join(map(lambda x: "<td %s>%s</td>" % (css_class, formatnumber(x, i)), row[1:3]))
			if row[3]<0:
				css_class = css_class + 'style="color:#FF0000"'
			tr = tr + "<td %s>%.1f</td></tr>" % (css_class, row[3]*10000)
		else:
			tr = tr + "".join(map(lambda x: "<td %s>%s</td>" % (css_class, formatnumber(x, i)), row[1:]))
			tr = tr + "</tr>"
		trs=trs+tr

	return template % (th, trs)

def stop():
    sys.stderr.close()

def main():
	tday = datetime.today()
	t_now = datetime.now()

	df = read_cmitem("OSPG Config.SINGAPORE.RateChart")

	tmr = datetime.today()+timedelta(days=1)
	dstr = tmr.strftime("%Y%m%d")

	df_official = calcOfficial(df, tday)
	#stop at 7am Asia time to restart and roll official
	while True:
		if t_now < datetime.strptime(dstr+"8", "%Y%m%d%H"):
			logger.info("started")
			dfreport = concat([df['Quote'], calcLIVE(df), df_official],axis=1)
			dfreport["Change"] = dfreport["LIVE"] - dfreport["OFFICIAL"]
			dfreport["Change"] = dfreport["Change"]

			#sending email
			ts = datetime.strftime(datetime.now(), "%d/%m/%Y %H:%M:%S")
			sender="fx_hybrid_support_asia@asia.bnpparibas.com"
			to = ['karim.mehdi@uk.bnpparibas.com','elise.balme@uk.bnpparibas.com','bertrand.baraduc@uk.bnpparibas.com']
			#to = ['wei.ren@asia.bnpparibas.com']
			cc=['SG.IT.IRG@asia.bnpparibas.com']
			html = reporthtml(dfreport, ts)
			open(r"D:\log.html", "w").write(html)
			sendemail(html, sender, to, cc, "PriceChangeSnapshot", ts, [])
		else:
			tday = datetime.today()
			if tday.weekday()!=5 or tday.weekday()!=6:
				tmr = datetime.today()+timedelta(days=1)
				dstr = tmr.strftime("%Y%m%d")
				df_official = calcOfficial(df, tday)

		#loop
		time.sleep(15*60)
		t_now = datetime.now()

if __name__ == '__main__':
	main()
	

