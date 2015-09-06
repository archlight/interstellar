import os
import argparse
import logging

from datetime import datetime
from tools.dbutil import maddb, mongodb
from tools.otherutil import dateoffset

cmd = " --no-tfc"

def quote(s):
	return '"'+s+'"'

if __name__ == '__main__':
	
	parser = argparse.ArgumentParser()
	parser.add_argument('--book', action='store', help='book or deal to run on', required=False)
	parser.add_argument('--test', action='store', help='test folder', required=False)
	parser.add_argument('--dayoffset', action='store', help='offset to base date', required=True)
	parser.add_argument('--jobs', action='append', help='Jobs to run', required=False)
	parser.add_argument('--batch', action='store', help='batch name', required=True)
	parser.add_argument('--maddb', action='store', help='mad instance name', required=True)
	
	args = parser.parse_args()

	if "ccyclose" in args.batch.lower() or "morning 123" in args.batch.lower():
		dayoffset = int(args.dayoffset) + 1
	else:
		dayoffset = int(args.dayoffset)

	basedt = dateoffset(datetime.today(), dayoffset, "%d/%m/%Y")
	request = {}
	request["user-name"] = os.environ["COMPUTERNAME"]
	request["sub-book"] = args.book

	mongo = mongodb('mongodb://localhost:3001/', None)

	if args.book:
		cmd = cmd + ' --no-fltr --sub-book %s %s' % ("123", quote(args.book))

	if args.jobs:
		cmd = cmd + "" + " ".join(map(lambda x: "--job "+ quote(x), args.jobs))

	cmd = " ".join([quote(args.batch), args.maddb]) + cmd

	print(cmd)




