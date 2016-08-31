# -*- coding: utf8 -*-
import sys
import time 
import datetime
#import threading
from threading import Thread

from pywebsocketserver.server import SocketServer
from pywebsocketserver.baseio import BaseIO
import subprocess
from Queue import Queue, Empty

from eventType import *
from vtFunction import *
from vtEngine import *
from json import * 
import json
from collections import OrderedDict

import chardet


import ast

from vtGateway import *

from uiMainWindow import *
from vtStrategy import *




class MyIO(BaseIO):
    
    def __init__(self,mainEngine=None,eventEngine=None): 
        #引擎集合
        self.engine = {}
        self.strategy = {}
        
        
        #headerDict
        self.markHeaderDict = OrderedDict()
        self.markHeaderList = []
        self.contractHeaderDict = OrderedDict()
        self.contractHeaderList=[]
        self.accountHeaderDict = OrderedDict()
        self.accountHeaderList=[]
        self.positionHeaderDict = OrderedDict()
        self.positionHeaderList=[]
        self.tradeHeaderDict = OrderedDict()
        self.tradeheaderList = []
        self.orderHeaderDict = OrderedDict()
        self.orderHeaderList = [] 
        
        
        #init
        self.initMarkHeaderDict()#行情
        self.initContractHeaderDict()#合约
        self.initAccountHeaderDict()#账户
        self.initPositionHeaderDict()#持仓
        self.initTradeHeaderDict()#交易
        self.initOrderHeaderDict()#委托
        
        self.__queue = Queue()
        
        self.__thread = Thread(target = self.__run)
        self.__thread.start()
        
        self.user_dict = OrderedDict()
        
        #存储
        self.position = {}
        #self.short_postion = {}
        
        
     
    
    def onData(self,uid,text):
        #print "IIIIIIIIIIIIIIIIIIIIIIDDDDDDDDDDDDDDDDDDDDDDDDDDDDD",uid,text
        text_dict = json.loads(text)
       
        if(text_dict['type']=="CONNECT"):
            print "CONNECT",text_dict['content']
        #登录   
        elif(text_dict['type']=="LOGIN"):
            print "LOGIN"
            self.engine[uid].connect('CTP')
            print "the information of login is "+text
        # 订阅合约    
        elif(text_dict['type']=="SUBSCRIBE"):
            print "SUBSCRIBE"
            req = VtSubscribeReq()
            req.symbol = text_dict['symbol']
            #req.exchange = exchange
            #req.currency = currency
            #req.productClass = productClass
            self.engine[uid].subscribe(req,'CTP')
        elif(text_dict['type']=="SENDORDER"):
            print "SENDORDER"
            req = VtOrderReq()
            req.symbol = str(text_dict['symbol'])#没有str功能时，显示错误，没有该合约，估计与编码有关
            
            if text_dict['direction'] == "long":
                req.direction = DIRECTION_LONG
            else: 
                req.direction = DIRECTION_SHORT
            if text_dict['offset'] == "open":
                req.offset = OFFSET_OPEN
            else:
                req.offset = OFFSET_CLOSE
            req.volume = text_dict['quantity']
            req.price = text_dict['price']
            req.priceType = PRICETYPE_LIMITPRICE
            
            self.engine[uid].sendOrder(req,'CTP')
           
            print req.symbol,req.direction,req.offset,req.volume,req.price,req.priceType
            
        elif(text_dict['type']=="AUTO-TRADE"):
            if(text_dict['strategy']=="1"):
                print u"启动策略1"
                self.strategy[uid].start(text_dict)
            
        
        
    def onConnect(self,uid):
        print "start onConnetct",uid
        self.engine[uid]=MainEngine(uid)
        self.engine[uid].eventEngine.register(EVENT_TICK,self.onTick)
        self.engine[uid].eventEngine.register(EVENT_LAST_CONTRACT,self.onLastContract)
        self.engine[uid].eventEngine.register(EVENT_ERROR,self.onError)
        self.engine[uid].eventEngine.register(EVENT_ACCOUNT,self.onAccount)
        self.engine[uid].eventEngine.register(EVENT_LOG,self.onLog)
        self.engine[uid].eventEngine.register(EVENT_POSITION,self.onPosition)
        self.engine[uid].eventEngine.register(EVENT_TRADE,self.onTrade)
        self.engine[uid].eventEngine.register(EVENT_ORDER,self.onOrder)
        self.strategy[uid] = Stratege(self.engine[uid])
        
        print "end onConnect"
        


    def __run(self):
        while True:
            try:
                data = self.__queue.get()
                print u"用户ID:",data['uid']
                self.sendData(data['uid'],json.dumps(data))
            except Empty:
                time.sleep(.01)   

    #推送TICK数据            
    def onTick(self,event):
        self.tick = {}
        self.tick['uid'] = event.uid_
        self.tick['type'] = event.type_
        data = event.dict_['data']
        for n, header in enumerate(self.markHeaderList):
            content = safeUnicode(data.__getattribute__(header))
            self.tick[header]=content
        self.__queue.put(self.tick)
        
    #推送合约基础信息    
    def onLastContract(self,event):
        self.contract = {}
        #print u"用户ID:",event.uid_
        self.contract['uid'] = event.uid_
        self.contract['type'] = event.type_
        data = self.engine[event.uid_].getAllContractsDict()
        for n,key in enumerate(data.keys()):
            temp = OrderedDict()
            for n,header in enumerate(self.contractHeaderList):
                content = safeUnicode(data[key].__getattribute__(header))
                temp[header]=content
            self.contract[key]=temp
            
        self.__queue.put(self.contract)
        
    #推送用户账户信息
    def onAccount(self,event):
        self.account = {}
        self.account['uid']=event.uid_
        self.account['type']=event.type_
        data = event.dict_['data']
        for n, header in enumerate(self.accountHeaderList):
            content = safeUnicode(data.__getattribute__(header))
            self.account[self.accountHeaderDict[header]['chinese']]=content
        self.__queue.put(self.account)
        
        pass
    def onError(self,event):
        pass
    def onLog(self,event):
        pass
    def onPosition(self,event):
        event_dict = {}
        event_dict['uid'] = event.uid_
        event_dict['type'] = event.type_
        data = event.dict_['data']
        for n, header in enumerate(self.positionHeaderList):
            content = safeUnicode(data.__getattribute__(header))
            event_dict[self.positionHeaderDict[header]['chinese']]=content
        self.__queue.put(event_dict)
        
        #print data.symbol+data.direction
        self.position[data.symbol+data.direction] = event_dict
       # print "yaorengui",event.uid_
        #if(event.uid_==None):
            #print "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",data.symbol
        #self.strategy[event.uid_].setPosition(self.position)
        
        
        
        pass
    def onTrade(self,event):
        header = self.tradeheaderList
        data_dict = {}
        data_dict['uid'] = event.uid_
        data_dict['type'] = event.type_
        data_dict['header_english']=self.tradeHeaderDict.keys()
        data_dict['header_chinese']=self.tradeHeaderDict.values()
        temp = {}
        data = event.dict_['data']
        for n, header in enumerate(header):
            content = safeUnicode(data.__getattribute__(header))
            temp[header]=content
        data_dict['data']=temp
        self.__queue.put(data_dict)
        
    
    def onOrder(self,event):
        header = self.orderHeaderList
        data_dict = {}
        data_dict['uid'] = event.uid_
        data_dict['type'] = event.type_
        data_dict['header_english']=self.orderHeaderDict.keys()
        data_dict['header_chinese']=self.orderHeaderDict.values()
        temp = {}
        data = event.dict_['data']
        for n, header in enumerate(header):
            content = safeUnicode(data.__getattribute__(header))
            temp[header]=content
        data_dict['data']=temp
        self.__queue.put(data_dict)        
        
    
        
    def put_test(self,num):
        self.tick = {}
        self.tick['type']="eTick1"
        self.tick['symbol']=num
        self.tick['vtSymbol']="IF1604"
        self.tick['lastPrice']="16.2"
        
        #self.tick['time']=datetime.datetime.now()
        self.__queue.put(json.dumps(self.tick))
        #print "put_test"
       
                
    def get(self):
        return self.__queue.get() 
    
    #初始化头字典
    
    def initMarkHeaderDict(self):
        d=OrderedDict()
        d['symbol'] = {'chinese':u'合约代码'}
        d['vtSymbol'] = {'chinese':u'名称'}
        d['lastPrice'] = {'chinese':u'最新价'}
        d['volume'] = {'chinese':u'成交量'}
        d['openInterest'] = {'chinese':u'持仓量'}
        d['openPrice'] = {'chinese':u'开盘价'}
        d['highPrice'] = {'chinese':u'最高价'}
        d['lowPrice'] = {'chinese':u'最低价'}
        d['bidPrice1'] = {'chinese':u'买一价'}
        d['bidVolume1'] = {'chinese':u'买一量'}
        d['askPrice1'] = {'chinese':u'卖一价'}
        d['askVolume1'] = {'chinese':u'卖一量'}
        d['time'] = {'chinese':u'时间'}
        d['gatewayName'] = {'chinese':u'接口'}
        self.markHeaderDict=d
        self.markHeaderList = d.keys()
        
    def initContractHeaderDict(self):
        d = OrderedDict()
        d['symbol'] = {'chinese':u'合约代码'}
        d['exchange'] = {'chinese':u'交易所'}
        d['vtSymbol'] = {'chinese':u'vt系统代码'}
        d['name'] = {'chinese':u'名称'}
        d['productClass'] = {'chinese':u'合约类型'}
        d['size'] = {'chinese':u'大小'}
        d['priceTick'] = {'chinese':u'最小价格变动'}
        self.contractHeaderDict = d
        self.contractHeaderList = d.keys()
        
    def initAccountHeaderDict(self):
        d = OrderedDict()
        d['accountID'] = {'chinese':u'账户'}
        d['preBalance'] = {'chinese':u'昨结'}
        d['balance'] = {'chinese':u'净值'}
        d['available'] = {'chinese':u'可用'}
        d['commission'] = {'chinese':u'手续费'}
        d['margin'] = {'chinese':u'保证金'}
        d['closeProfit'] = {'chinese':u'平仓盈亏'}
        d['positionProfit'] = {'chinese':u'持仓盈亏'}
        d['gatewayName'] = {'chinese':u'接口'} 
        self.accountHeaderDict = d
        self.accountHeaderList = d.keys()
        
    def initPositionHeaderDict(self):
        d = OrderedDict()
        d['symbol'] = {'chinese':u'合约代码'}
        d['vtSymbol'] = {'chinese':u'名称'}
        d['direction'] = {'chinese':u'方向'}
        d['position'] = {'chinese':u'持仓量'}
        d['ydPosition'] = {'chinese':u'昨持仓'}
        d['frozen'] = {'chinese':u'冻结量'}
        d['price'] = {'chinese':u'价格'}
        d['gatewayName'] = {'chinese':u'接口'}   
        self.positionHeaderDict = d
        self.positionHeaderList = d.keys()
        
    def initTradeHeaderDict(self):
        d = OrderedDict()
        d['tradeID'] = {'chinese':u'成交编号'}
        d['orderID'] = {'chinese':u'委托编号'}
        d['symbol'] = {'chinese':u'合约代码'}
        d['vtSymbol'] = {'chinese':u'名称'}
        d['direction'] = {'chinese':u'方向'}
        d['offset'] = {'chinese':u'开平'}
        d['price'] = {'chinese':u'价格'}
        d['volume'] = {'chinese':u'数量'}
        d['tradeTime'] = {'chinese':u'成交时间'}
        d['gatewayName'] = {'chinese':u'接口'}
        self.tradeHeaderDict = d
        self.tradeheaderList = d.keys()
        
    def initOrderHeaderDict(self):
        d = OrderedDict()
        d['orderID'] = {'chinese':u'委托编号'}
        d['symbol'] = {'chinese':u'合约代码'}
        d['vtSymbol'] = {'chinese':u'名称'}
        d['direction'] = {'chinese':u'方向'}
        d['offset'] = {'chinese':u'开平'}
        d['price'] = {'chinese':u'价格'}
        d['totalVolume'] = {'chinese':u'委托数量'}
        d['tradedVolume'] = {'chinese':u'成交数量'}
        d['status'] = {'chinese':u'状态'}
        d['orderTime'] = {'chinese':u'委托时间'}
        d['cancelTime'] = {'chinese':u'撤销时间'}
        d['frontID'] = {'chinese':u'前置编号'}
        d['sessionID'] = {'chinese':u'会话编号'}
        d['gatewayName'] = {'chinese':u'接口'}   
        self.orderHeaderDict = d
        self.orderHeaderList = d.keys()
        
def main():
    port = 8080
    myIo = MyIO()
    SocketServer(port,myIo).start()
    
    #mainEngine = MainEngine(-1)
    
    
    
    
    #mainWindow = MainWindow(mainEngine, mainEngine.eventEngine)
    #mainEngine.connect('CTP')
    #req = VtOrderReq()
    #req.symbol = "IF1604"
    #req.direction = DIRECTION_LONG
    #req.offset = OFFSET_OPEN
    #req.price = 123.4
    #req.volume = 1
    #req.priceType = PRICETYPE_LIMITPRICE
    
    
    #while(True):
        #try:
            #print "while"
            #mainEngine.senderOrder(req,'CTP')
            #mainEngine.sendOrder1(req.symbol,req.price,req.volume,req.priceType,req.direction,req.offset, 'CTP')
        #except:
            #time.sleep(1)
    
    
if __name__ =='__main__':
    main()
    pass
    
        