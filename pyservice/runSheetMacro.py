import argparse
import logging
import logging.handlers
import socket
import sqlite3
from pymongo import MongoClient
from datetime import datetime
import os

def launchExcel(compVersion=None, sheet=None, macro=None, args=None, toQuit=True):
    import win32com.client as dyn
    import win32process
    import os
    import datetime
    myExcel = dyn.DispatchEx('Excel.Application')
    processId=win32process.GetWindowThreadProcessId(myExcel.Hwnd)[1]
    logging.info('ProcessId: '+str(processId))
    myExcel.Visible=True
    myExcel.Workbooks.Open(r'\\sinemc114042\swaps\OSPG\Lib\ospg-frozen.xla',False,True)
    myExcel.Workbooks.Open(r'\\SINS00300003\INFDATA\BANK\_FPG0001000VEN002\FIIT_UTILS\ospg.xla',False,True) # new
    myExcel.DisplayAlerts = False
    if compVersion is None:
        myExcel.Application.Run('OSPG_LoadAddIns', 'Components')
    else:
        logging.info('Special Components version: ' + compVersion)
        myExcel.Application.Run('OSPG_LoadAddIns', 'Components',compVersion)
    if sheet is not None:
        logging.info('Opening sheet: ' + sheet)
        #myExcel.Application.EnableEvents(False)
        myWorkBook =  myExcel.Workbooks.Open(sheet,False,True)
        myExcel.Application.Run('EnableLogFile', True,r'\\sinemc114042\risktech\tools\Log\runSheetMacro' + os.path.sep + os.path.basename(sheet) + '.' + datetime.date.today().strftime('%Y-%m-%d') + '.' + str(processId) + '.log')
        logging.info('Removing External links')
        isblank = macro is None or macro == 'BLANK'
        
        if not isblank:
            myExcel.Application.Run('OSPG_RemoveExternalLinks')

            logging.info('Opening macro: ' + macro)
            if args is not None:
                logging.info('Arguments' + str(args))
                myExcel.Application.Run(macro,*args)
            else:
                myExcel.Application.Run(macro)

            if myWorkBook is not None:
                myWorkBook.Saved = True
                myWorkBook.Close(False)
                logging.info('Closed Workbook: ' + str(processId))
                myWorkBook = None

    if toQuit:
        logging.info('Quitting')
        
        if myExcel is not None and sheet is not None:
            myExcel.Quit()
            pass
        import time
        time.sleep(2)
        if myExcel is not None and sheet is not None:
            import os
            logging.warn('Failed to quit the book, kill by process id: ' + str(processId))
            os.kill(processId, 9)

class mongodb():

    def __init__(self, url):
        client = MongoClient(url)
        self.meteor = client.meteor

    def jobstart(self, taskname):
        ts = datetime.now()
        return self.meteor.scheduler.insert({"taskname":taskname, "start_time":ts, "state":"EX"})

    def jobend(self, _id, state):
        ts = datetime.now()
        return self.meteor.scheduler.update({"_id":_id}, {"$set":{"state":state, "end_time":ts}})

if __name__ == '__main__':

    mdb = mongodb('mongodb://localhost:3001/')
    try:
        rootLogger = logging.getLogger()
        handler = logging.handlers.TimedRotatingFileHandler(r'\\sinemc114042\risktech\tools\Log\runSheetMacro\runSheetMacro'+socket.gethostname()+'.log','midnight')
        handler.setFormatter(logging.Formatter('%(asctime)s.%(msecs).03d %(levelname)-8s [%(processName)s-%(threadName)s] %(name)s - %(message)s'))
        rootLogger.addHandler(handler)

        rootLogger.setLevel('DEBUG')
        parser = argparse.ArgumentParser()
        parser.add_argument('--compVersion', action='store', help='Components Version', required=False)
        parser.add_argument('--toQuit', action='store', help='ToQuitOrNotToQuit', required=False)
        parser.add_argument('--sheet', action='store', help='Worksheet', required=False)
        parser.add_argument('--macro', action='store', help='Macro', required=False)
        parser.add_argument('--taskName', action='store', help='Macro', required=False)                
        parser.add_argument('--args', action='store', help='Macro', required=False, nargs = '*')

        args = parser.parse_args()
        if args.toQuit is None:
            toQuit = True
        else:
            toQuit = not(args.toQuit.lower() == 'false')

        if not args.taskName:
            if os.path.exists(args.sheet):
                taskName = args.sheet.split(os.path.sep)[-1].split(".")[0]
            

        
        _id = mdb.jobstart(taskName)    
        #launchExcel(args.compVersion,args.sheet,args.macro,args.args,toQuit)
        mdb.jobend(_id, "OK")
    except Exception as e:
        mdb.jobend(_id, "KO")
        print(str(e))
