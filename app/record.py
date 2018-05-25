from flask import render_template, redirect, url_for, abort, flash, request,\
    current_app, make_response, g, jsonify
import os,random
import pygal
import threading
import sys
from . import app
import time

def get_procinfo(filename):
    try:
      fh = open(filename, 'r')
      data = fh.read()
    except IOError:
      print("Error: cant open file %s" % (filename))
      return None
    else:
      fh.close()
    return data

def get_cmdout(cmdline):
    try:
      file = os.popen(cmdline) 
      outputs = file.read()
    except IOError:
      print("Error: cant run cmd %s" % (cmdline))
      return None
    else:
      file.close()
    return outputs

class RecordDate():
    def __init__(self, **kwargs):
        self.data = []
        self.len = 120
        self.cnt = 0
        if kwargs:
            self.len = kwargs['len']

    def add(self, val):
        if self.cnt >= self.len:
            self.data.pop(0)
        else:
            self.cnt+=1
        self.data.append(val)
        
    def dump(self):
        for val in self.data:
            print(val.getdata('all'))
    
    def getlast(self,name):
        return [self.data[-1].time, self.data[-1].getdata(name)]
        
    def getline(self, name):
        ret = []
        d = self.len - self.cnt
        for val in self.data:
            if d > 0:  #数据不够时填充
                for i in range(d):
                    ret.append([val.time,val.getdata(name)])
                d = 0
            ret.append([val.time,val.getdata(name)])
        return ret
    
#定义二维数组，存放固定长度的数据
class Record():
    data = []
    rows = 1
    columns = 10
    cnt = [0]

    def __init__(self, **kwargs):
        if kwargs:
            self.rows = kwargs['rows']
            self.columns = kwargs['columns']
            self.data = [([] * self.columns) for i in range(self.rows)] #二维数组的创建方法
            self.cnt = [0 for i in range(self.rows)]
            
    def add(self, row, val):
        if self.cnt[row] >= self.columns:
            self.data[row].pop(0)
        else:
            self.cnt[row]+=1
        self.data[row].append(val)

class Loadavg():
    rec = Record(rows=3,columns=50)

    def __init__(self, **kwargs):
        self.load1 = 0 
        self.load5 = 0
        self.load15 = 0
        self.time = 0
    
    def update(self):
        avg = get_procinfo('/proc/loadavg')
        self.time = int(time.time() * 1000)
        self.load1 = float(avg.split(' ')[0])
        self.load5 = float(avg.split(' ')[1])
        self.load15 = float(avg.split(' ')[2])
        self.rec.add(0,self.load1)
        self.rec.add(1,self.load5)
        self.rec.add(2,self.load15)
        return [self.load1,self.load5,self.load15]
        #print(self.rec.data[0])
        #print(self.rec.data[1])
        #print(self.rec.data[2])
    
    def getdata(self,name):
        if name == 'load1':
            return self.load1
        elif name == 'load5':
            return self.load5
        elif name == 'load15':
            return self.load15
        else:
            return [self.load1,self.load5,self.load15]
    
    def draw(self):
        self.update()
        line_chart = pygal.Line(height=200)
        line_chart.title = 'Load Avg'
        line_chart.x_labels = map(str, range(0, 50))
        line_chart.add('1分钟', self.rec.data[0])
        line_chart.add('5分钟', self.rec.data[1])
        line_chart.add('15分钟', self.rec.data[2])

        #chart = bar_chart.render(disable_xml_declaration = True) #直接写入svg格式数据，存在不能交互的问题
        #return bar_chart.render_response() 直接返回xml格式的页面
        line_chart.render_to_file('app/static/loadavg.svg') 
        return line_chart.render_data_uri() #编码成base uri格式，以嵌入到html代码中

class Stat():
    def __init__(self, **kwargs):
        self.cpunum = 0
        self.cpu = {}
        self.intr = []
        self.ctxt = 0
        self.btime = 0
        self.processes = 0
        self.procs_running = 0
        self.procs_blocked = 0
        self.softirq = []
        self.time = 0
        self.diffdata = []
        self.diffctxt = 0
        self.diffprocesses = 0
        self.difftime = 0
        self.diffsoftirq = []
        self.diffintr = {}
    
    def getstat(self):
        self.time = int(time.time() * 1000)
        data = get_procinfo('/proc/stat')
        if data == None:
            return
        data = data.split('\n')
        self.cpunum = 0
        for line in data:
            line = line.split(' ')
            while '' in line:
                line.remove('')
            if line:
                if 'cpu' in line[0]:
                    if line[0] == 'cpu' :
                        self.cpu['all'] = list(map(int, line[1:]))
                    else:
                        num = line[0][3:]
                        self.cpu[num] = list(map(int, line[1:]))
                        self.cpunum +=1
                elif 'intr' in line[0]:
                    self.intr = list(map(int, line[1:]))
                elif 'softirq' in line[0]:
                    self.softirq = list(map(int, line[1:]))
                elif 'ctxt' in line[0]:
                    self.ctxt = int(line[1])
                elif 'btime' in line[0]:
                    self.btime = int(line[1])
                elif 'processes' in line[0]:
                    self.processes = int(line[1])
                elif 'procs_running' in line[0]:
                    self.procs_running = int(line[1])
                elif 'procs_blocked' in line[0]:
                    self.procs_blocked = int(line[1])

    def diff(self,oldstat):
        if oldstat.cpunum != 0:
            diff_user = self.cpu['all'][0] - oldstat.cpu['all'][0]
            diff_nice = self.cpu['all'][1] - oldstat.cpu['all'][1]
            diff_system = self.cpu['all'][2] - oldstat.cpu['all'][2]
            diff_idle = self.cpu['all'][3] - oldstat.cpu['all'][3]
            diff_iowait = self.cpu['all'][4] - oldstat.cpu['all'][4]
            diff_irq = self.cpu['all'][5] - oldstat.cpu['all'][5]
            diff_softirq = self.cpu['all'][6] - oldstat.cpu['all'][6]
            diff_steal = self.cpu['all'][7] - oldstat.cpu['all'][7]
            sum = diff_user+diff_nice+diff_system+diff_idle+diff_iowait+diff_irq+diff_softirq+diff_steal
            if sum != 0:
                self.diffdata = [round(diff_user*100/sum,2),round(diff_nice*100/sum,2),\
                        round(diff_system*100/sum,2),round(diff_idle*100/sum,2),\
                        round(diff_iowait*100/sum,2),round(diff_irq*100/sum,2),\
                        round(diff_softirq*100/sum,2),round(diff_steal*100/sum,2)]
                print(self.diffdata)
            self.diffctxt = self.ctxt - oldstat.ctxt
            self.diffprocesses = self.processes - oldstat.processes
            self.difftime = self.time - oldstat.time
            
            self.diffsoftirq=[]  
            for i in range(0,len(oldstat.softirq)):  
                summm=self.softirq[i] - oldstat.softirq[i]
                self.diffsoftirq.append(summm) 
            
            self.diffintr={}  
            for i in range(0,len(oldstat.intr)):  
                summm=self.intr[i] - oldstat.intr[i]
                if summm > 0:
                    self.diffintr[i] = summm
            print(self.diffintr)

    def getdata(self,name):
        if len(self.diffdata) > 0:
            if name == 'user':
                return self.diffdata[0]
            elif name == 'nice':
                return self.diffdata[1]
            elif name == 'system':
                return self.diffdata[2]
            elif name == 'idle':
                return self.diffdata[3]
            elif name == 'iowait':
                return self.diffdata[4]
            elif name == 'irq':
                return self.diffdata[5]
            elif name == 'softirq':
                return self.diffdata[6]
            elif name == 'steal':
                return self.diffdata[7]
            elif name == 'utilization':
                return self.diffdata

        if name == 'run':
            return self.procs_running
        elif name == 'blocked':
            return self.procs_blocked
        elif name == 'ctxt':
            return self.diffctxt
        elif name == 'fork':
            return self.diffprocesses
        elif name == 'misc':
            return [self.diffctxt, self.diffprocesses,self.procs_running,self.procs_blocked]
        
        if len(self.diffsoftirq) > 0:
            if name == 's_hi':
                return self.diffsoftirq[1]
            elif name == 's_timer':
                return self.diffsoftirq[2]
            elif name == 's_net_tx':
                return self.diffsoftirq[3]
            elif name == 's_net_rx':
                return self.diffsoftirq[4]
            elif name == 's_block':
                return self.diffsoftirq[5]
            elif name == 's_block_iopoll':
                return self.diffsoftirq[6]
            elif name == 's_tasklet':
                return self.diffsoftirq[7]
            elif name == 's_sched':
                return self.diffsoftirq[8]
            elif name == 's_hrtimer':
                return self.diffsoftirq[9]
            elif name == 's_rcu':
                return self.diffsoftirq[10]
            elif name == 's_softirq':
                return self.diffsoftirq
        
        if len(self.diffintr) > 0:
            if name == 'h_all':
                return self.diffintr[0]
            elif name == 'h_irq':
                return self.diffintr
        return 0
        
class Process():
    def __init__(self, **kwargs):
        self.stat = []
        self.maps = []
        self.status = {}
        self.pid = 1
        self.ppid = 0
        self.pgid = 0
        self.sid = 0
        self.VmPeak = None
        self.RssFile = 0
        self.utime = 0
        self.stime = 0
        self.cputime = 0
        if kwargs:
            self.pid = kwargs['pid']
    
    def getstat(self):
        data = get_procinfo('/proc/%d/stat' % (self.pid))
        if data == None:
            return 
        data=data[:-1]                   #去除回车
        first_parenthesis = data.find('(')
        last_parenthesis = data.rfind(')')
        temp = data[last_parenthesis+2:]
        self.stat.append(int(data[0:first_parenthesis-1]))   #获取pid
        self.stat.append(data[first_parenthesis+1:last_parenthesis]) #获取进程名
        self.stat.extend(temp.split(' ')) #列表加列表需要使用extend
        #print(self.stat)
        self.utime = int(self.stat[13])
        self.stime = int(self.stat[14])
        self.cputime = self.utime + self.stime
        #self.cputime = pow(self.cputime, 1/3)
        return self.stat

    def getcomm(self):
        self.comm = get_procinfo('/proc/%d/comm' % (self.pid))
        return self.comm

    def getcmdline(self):
        self.cmdline = get_procinfo('/proc/%d/cmdline' % (self.pid))
        return self.cmdline

    def getstatus(self):
        data = get_procinfo('/proc/%d/status' % (self.pid))
        if data == None:
            return
        data = data.split('\n')
        for line in data:
            if line:
                line=line.replace('\t','')
                line=line.split(':')
                self.status[line[0]] = line[1]
                if line[0] == 'VmPeak':
                    self.VmPeak = int(self.status['VmPeak'].replace('kB',''))
                elif line[0] == 'VmSize':
                    self.VmSize = int(self.status['VmSize'].replace('kB',''))
                elif line[0] == 'VmHWM':
                    self.VmHWM = int(self.status['VmHWM'].replace('kB',''))
                elif line[0] == 'VmRSS':
                    self.VmRSS = int(self.status['VmRSS'].replace('kB',''))
                elif line[0] == 'VmData':
                    self.VmData = int(self.status['VmData'].replace('kB',''))
                elif line[0] == 'VmStk':
                    self.VmStk = int(self.status['VmStk'].replace('kB',''))
                elif line[0] == 'VmLck':
                    self.VmLck = int(self.status['VmLck'].replace('kB',''))
                elif line[0] == 'VmPin':
                    self.VmPin = int(self.status['VmPin'].replace('kB',''))
                elif line[0] == 'VmExe':
                    self.VmExe = int(self.status['VmExe'].replace('kB',''))
                elif line[0] == 'VmLib':
                    self.VmLib = int(self.status['VmLib'].replace('kB',''))
                elif line[0] == 'VmPTE':
                    self.VmPTE = int(self.status['VmPTE'].replace('kB',''))
                elif line[0] == 'VmSwap':
                    self.VmSwap = int(self.status['VmSwap'].replace('kB',''))
        if self.VmPeak:
            return [self.VmSize,self.VmStk,self.VmData,self.VmLib,self.VmExe,self.utime,self.stime]

    def getstatm(self):
        data = get_procinfo('/proc/%d/statm' % (self.pid))
        data = data.split(' ')
        self.RssFile = int(data[2]) * 4   #这里假设页大小为4096
        print(self.RssFile)

    def getmaps(self):
        data = get_procinfo('/proc/%d/maps' % (self.pid))
        if data == None:
            return
        data = data.split('\n')
        for line in data:
            if line:
                line=line.split(' ')
                while '' in line:
                    line.remove('')
                self.maps.append(line)
        print(self.maps)
        
class Processes():
    def __init__(self, **kwargs):
        self.pidcnt = 0
        self.process_dict = {}
        self.ordered = []
        if kwargs:
            pass

    def scan(self):
        self.pidcnt = 0
        outputs = get_cmdout('ls /proc/') 
        lists = outputs.split('\n')
        print(lists)
        for list in lists:
            if list.isdigit():
                process = Process(pid = int(list))
                ret = process.getstat()
                self.pidcnt += 1
                if ret:
                    process.getstatus()
                    self.process_dict[process.pid] = process
        print("total process %d"%(self.pidcnt))
        return self.process_dict
        
    def gengv(self):
        fh = open('app/static/pstree', 'w')
        fh.write("digraph ptree {\n node [ style = filled ];\n")
        for key in self.process_dict:
            if self.process_dict[key].stat[40] == '0':
                color = '#96cdcd3f'
            elif self.process_dict[key].stat[40] == '1':
                color = '#cdaf953f'
            elif self.process_dict[key].stat[40] == '2':
                color = '#7ccd7c3f'
            elif self.process_dict[key].stat[40] == '3':
                color = '#ffa07a3f'
            elif self.process_dict[key].stat[40] == '5':
                color = '#6ca6cd3f'
            else:
                color = '#FFFFFFFF'
            fh.write("    \"%s\" -> \"%s\" [ ];\n"%(self.process_dict[key].stat[3],self.process_dict[key].stat[0]))
            fh.write("    \"%s\" [ label = \"%s\" color = \"%s\" ];\n"%(self.process_dict[key].stat[0],self.process_dict[key].stat[1],color))
        fh.write("}")
        fh.close()
        os.system("neato -Tsvg -Nfontsize=12 -Elen=1.9 app/static/pstree -o app/static/pstree.svg")
        

class ScanTimer():
    timer = None
    intval = 1

    def start(self):
        self.scan_process()
        timer = threading.Timer(self.intval, self.start)
        timer.start()

    def scan_process(self):
        ctx=app.app_context()  
        ctx.push() 
        #loadavg
        if not hasattr(current_app,'g_loadavg'):
            current_app.g_loadavg = RecordDate()
        loadavg = Loadavg()
        loadavg.update()
        current_app.g_loadavg.add(loadavg)
        print(current_app.g_loadavg.getlast('load1'))
        
        #stat
        if not hasattr(current_app,'g_stat'):
            current_app.g_stat = RecordDate()
        newstat = Stat()
        newstat.getstat()
        if len(current_app.g_stat.data) > 0:
            newstat.diff(current_app.g_stat.data[-1])
        current_app.g_stat.add(newstat)
        
        ctx.pop() 