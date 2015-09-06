from datetime import datetime, timedelta
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from collections import defaultdict
import email
import email.mime.application
import logging
import subprocess

def xldate(d):
    # date(1901, 1, 1).toordinal() - 367
    return d.toordinal()-693594

def trunc(d):
    return datetime.strptime(datetime.strftime(d,"%d%m%Y"),"%d%m%Y")    

def dateoffset(d, offset, dateformat=""):
    scenario = d + timedelta(days=offset)
    if scenario.weekday() ==6:
        extra = 2 * offset/abs(offset)
    elif scenario.weekday()==5:
        extra = 1 * offset/abs(offset)
    else:
        extra = 0
    d = scenario + timedelta(days=extra)
    return d if not len(dateformat) else datetime.strftime(d, dateformat)

def tuplicate(t):
    return tuple(map(tuplicate, t)) if isinstance(t, (list, tuple)) else t

def totuple(a): 
    try: 
        if(len(a) > 1):
            return tuple(totuple(i) for i in a)
        else:
            return tuple3d(a) 
    except TypeError: 
        return a
    
def tuple3d(val, transpose=True):
    # dict
    if type(val) is dict:
        return (tuple(val.items()),)
    
    # scalar: not sequence type
    if not isinstance(val, (list, tuple)):
        return (((val,),),)

    # 1d sequence: Type of element[0] is not sequence
    if not (type(val[0]) is list or type(val[0]) is tuple):
        if not transpose:
            return ((tuple(val),),)
        else:
            return tuple3d([(x,) for x in val])

    # 2d sequence: Type of element[0][0] is not sequence
    if not (type(val[0][0]) is list or type(val[0][0]) is tuple):
        return tuplicate((tuple(val),))
    
    return val

#subprocess routine

def ntmadsubmit(batchcmds):
    
    def parseNTMadSubmit(oStr):
        d=defaultdict(list)
        for t in str(oStr).split("\\r\\n"):
            if len(t) and t[0]==" ":
                k, v = t.split(":")
                d[k.strip()].append(v.strip()) 
        return d

    ntmadsubmit_path = r"\\SINEMC114042\risktech\Tools\IRG\Utils\Mad_Utils\NTMadSubmit\NTMadSubmit.exe "
    
    if isinstance(batchcmds, str):
        batchcmds = [batchcmds]
        
    
    res = defaultdict(list)
    for batchcmd in batchcmds:
        if len(batchcmd):        
            cmdline = ntmadsubmit_path + batchcmd
                    
            logger = logging.getLogger(__name__)
            logger.info(cmdline)
        
            _, oRes = cmd(cmdline, parseNTMadSubmit, stdout="PIPE")
            if not "job_id" in oRes:
                raise Exception("Job Id not found. submission failed")
            else:
                res["job_id"].extend(oRes["job_id"])
                res["job_name"].extend(oRes["job name"])
                res["batchname"].extend(oRes["batchname"])
    return res

def cmd(cmdline, parse, stdout="PIPE"):
    retdict = {}
    if stdout == "PIPE":
        p = subprocess.Popen(cmdline, stdout=subprocess.PIPE)
        retdict = parse(str(p.stdout.read()))
    elif stdout == "DEVNULL":
        p = subprocess.Popen(cmdline, stdout=open(os.devnull, "wb"))
    else:
        p = subprocess.Popen(cmdline)
         
    return (p, retdict)

#email utilities

def sendemail(html, sender, to, cc, subject, suffix, attachments=[]):

    s = smtplib.SMTP("SINAPPSMTP001")
    
    msg = MIMEMultipart('related')

    msg['Subject'] = "%s %s" % (subject, suffix)
    msg['From'] = sender
    msg['To'] = ", ".join(to)
    msg['cc'] = ", ".join(cc)

    body = MIMEMultipart('alternative')
    msg.attach(body)
    
    body.attach(MIMEText(html, 'html'))
    #attachment
    for t in attachments:
        filename=r'x:\%s' % t
        fp=open(filename,'rb')
        att = email.mime.application.MIMEApplication(fp.read(),_subtype="html")
        fp.close()
        att.add_header('Content-Disposition','attachment',filename=t)
        msg.attach(att)
    
    for receipent in to+cc:
        s.sendmail(sender, receipent, msg.as_string())

def simplemail(txt, sender, to, subject):
    s = smtplib.SMTP("SINAPPSMTP001")
    msg=MIMEText(txt, 'plain')
    msg['From'] = sender
    msg['To'] = ", ".join(to)
    msg['Subject'] = subject
    
    for receipent in to:
        s.sendmail(sender, receipent, msg.as_string()) 