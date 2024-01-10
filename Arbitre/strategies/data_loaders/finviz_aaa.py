#!/usr/bin/env python
# coding:utf-8

from datetime import datetime
from os import mkdir as osMkdir
from os.path import exists as osPathExists, join as osPathJoin
from requests import get as requestsGet
from bs4 import BeautifulSoup
from pandas import DataFrame as pdDataframe, to_datetime as pdTo_datetime
from sqlalchemy import create_engine


# relative import
from sys import path;path.extend("..")
from common.Helpers.helpers import init_logger
from common.Helpers.proxy import getHttpProxy, getUserAgent
from analyst.analyst_helpers import get_FA_Sectors, convertDigits



proxyPool = getHttpProxy()
agentPool = getUserAgent() 

def getIndexs():
    SnP500 = 'https://finviz.com/screener.ashx?v=152&c=0,1,2,3,4,5,6,8,9,10,11,13,17,18,20,22,23,32,33,34,35,36,37,38,39,40,41,43,44,45,46,47,51,67,65,66&f=idx_sp500'
    MegaCap = 'https://finviz.com/screener.ashx?v=152&c=0,1,2,3,4,5,6,8,9,10,11,13,17,18,20,22,23,32,33,34,35,36,37,38,39,40,41,43,44,45,46,47,51,67,65,66&f=cap_mega'
    LargeCap = 'https://finviz.com/screener.ashx?v=152&c=0,1,2,3,4,5,6,8,9,10,11,13,17,18,20,22,23,32,33,34,35,36,37,38,39,40,41,43,44,45,46,47,51,67,65,66&f=cap_large'
    MidCap = 'https://finviz.com/screener.ashx?v=152&c=0,1,2,3,4,5,6,8,9,10,11,13,17,18,20,22,23,32,33,34,35,36,37,38,39,40,41,43,44,45,46,47,51,67,65,66&f=cap_mid'
    SmallCap = 'https://finviz.com/screener.ashx?v=152&c=0,1,2,3,4,5,6,8,9,10,11,13,17,18,20,22,23,32,33,34,35,36,37,38,39,40,41,43,44,45,46,47,51,67,65,66&f=cap_small'
    MicroCap = 'https://finviz.com/screener.ashx?v=152&c=0,1,2,3,4,5,6,8,9,10,11,13,17,18,20,22,23,32,33,34,35,36,37,38,39,40,41,43,44,45,46,47,51,67,65,66&f=cap_micro'

    indexs = [SnP500, MegaCap, LargeCap, MidCap, SmallCap, MicroCap]
    indexName = ["SnP500", "MegaCap", "LargeCap", "MidCap", "SmallCap", "MicroCap"]

    return indexs, indexName

def createWorkingDirectory(config, logger):
    try:
        # create directory and DB datas if not exists
        if not osPathExists(config.FS_TEMP): osMkdir(config.FS_TEMP)
        basePath = osPathJoin(config.FS_TEMP, "fa_finviz_aaa")
        if not osPathExists(basePath): osMkdir(basePath)

    except Exception as e:
        logger.error("{0} : error while trying to create temp/working directory : {1}".format(name, e))
        exit(1)
    return basePath

def getConnection(config):
    engine = create_engine(config.parser["ANALYST"]["ANALYST_DB_URI"])
    return engine



def scrapFinvizDatas(name, config, logger):
    basePath = createWorkingDirectory(config=config, logger=logger)
    engine = getConnection(config=config)
    sectors = get_FA_Sectors()
    rawURL = 'https://finviz.com/screener.ashx?v=152&c=0,1,2,3,4,5,6,8,9,10,11,13,17,18,20,22,23,32,33,34,35,36,37,38,39,40,41,43,44,45,46,47,51,67,65,66&f=sec_'

    # load datas
    allData = []
    for i in range(len(sectors)):
        try:
            logger.info("{0} : gathering data from '{1}' sector...".format(name, sectors[i]))

            tableStocks = []
            firstPage = True
            stocksAdded = 0

            while True: 
                URL = rawURL + sectors[i] + '&r=' + str(stocksAdded+1)
                page = requestsGet(URL, headers=next(agentPool), proxies = {"http": next(proxyPool)})
                soup = BeautifulSoup(page.content, 'html.parser')
                screener_data = soup.find(name='table', class_="styled-table-new is-rounded is-tabular-nums w-full screener_table")

                if not screener_data is None: rows = screener_data.find_all(name='tr')
                else: break

                if firstPage :
                    htmlHeader = rows[0] 
                    headersCells = [th.contents[0] for th in htmlHeader.find_all('th') if not th.find_all()]
                    headers = []
                    for cell in headersCells:
                        headers.append(cell.text.strip().lower())
                    headers.insert(1, "Ticker")
                    stocksAdded -= 1
                    firstPage = False 
                else:
                    rows = rows[1:]

                for row in rows:
                    stocksAdded += 1
                    cells = row.find_all('td')
                    rowStocks = []
                    for cell in cells:
                        rowStocks.append(cell.text.strip())
                    tableStocks.append(rowStocks)

                if stocksAdded % 20 > 0 : break

            # save datas
            df = pdDataframe(tableStocks[1:], columns=headers)
            df = df.applymap(convertDigits)
            df["Date"] = pdTo_datetime('now')
            df.to_csv(osPathJoin(basePath, "AAA - {0}.csv".format(sectors[i])), index=False, mode='w')
            logger.info("{0} : 'AAA - {1}.csv' file has been saved in directory : {2}".format(name, sectors[i], basePath))

            df.to_sql("AAA_{0}".format(sectors[i]), con=engine, if_exists="replace", index=False)
            logger.info("{0} : 'AAA_{1}' datas has been saved in database : {2}".format(name, sectors[i], engine.url))
            allData.extend(tableStocks[1:])

        except Exception as e:
            logger.error("{0} : error while trying to gather data from '{1}' sector : {2}".format(name, sectors[i], e))
            continue

    try:
        dfAllData = pdDataframe(allData, columns=headers)
        dfAllData = dfAllData.applymap(convertDigits)
        dfAllData["Date"] = pdTo_datetime('now')
        dfAllData.to_csv(osPathJoin(basePath, "AAA - all.csv"), index=False, mode='w')
        logger.info("{0} : 'AAA - all.csv' file has been saved in directory : {1}".format(name, basePath))

        dfAllData.to_sql("AAA_all", con=engine, if_exists="replace", index=False)
        logger.info("{0} : 'AAA_all' datas has been saved in database : {1}".format(name, engine.url))

    except Exception as e:
        logger.error("{0} : error while trying to save file 'AAA - AllData.csv' : {1}".format(name, e))



def loadMainIndex(name, config, logger):

    basePath = createWorkingDirectory(config=config, logger=logger)
    engine = getConnection(config=config)

    indexs, indexName = getIndexs()

    for i in range(len(indexs)):
        try:
            logger.info("{0} : gathering index from '{1}' index...".format(name, indexName[i]))

            tableIndex = []
            firstPage = True
            stocksAdded = 0

            while True: 
                URL = indexs[i] + '&r=' + str(stocksAdded+1)
                page = requestsGet(URL, headers=next(agentPool), proxies = {"http": next(proxyPool)})
                soup = BeautifulSoup(page.content, 'html.parser')
                screener_data = soup.find(name='table', class_="styled-table-new is-rounded is-tabular-nums w-full screener_table")

                if not screener_data is None: rows = screener_data.find_all(name='tr')
                else: break

                if firstPage :
                    htmlHeader = rows[0] 
                    headersCells = [th.contents[0] for th in htmlHeader.find_all('th') if not th.find_all()]
                    headers = []
                    for cell in headersCells:
                        headers.append(cell.text.strip())
                    headers.insert(1, "Ticker")
                    stocksAdded -= 1
                    firstPage = False 
                else:
                    rows = rows[1:]

                for row in rows:
                    stocksAdded += 1
                    cells = row.find_all('td')
                    rowStocks = []
                    for cell in cells:
                        rowStocks.append(cell.text.strip())
                    tableIndex.append(rowStocks)

                if stocksAdded % 20 > 0 : break

            df = pdDataframe(tableIndex[1:], columns=headers)
            df = df.applymap(convertDigits)
            df["Date"] = pdTo_datetime('now')
            df.to_csv(osPathJoin(basePath, "AAA - {0}.csv".format(indexName[i])), index=False, mode='w')
            logger.info("{0} : 'AAA - {1}.csv' file has been saved in directory : {2}".format(name, indexName[i], basePath))

            df.to_sql("AAA_{0}".format(indexName[i]), con=engine, if_exists="replace", index=False)
            logger.info("{0} : 'AAA_{1}' datas has been saved in database : {2}".format(name, indexName[i], engine.url))
            
        except Exception as e:
            logger.error("{0} : error while trying to gather index from '{1}' sector : {2}".format(name, indexName[i], e))
            continue

def run_finviz_data_loader(config, logger, name = "fa_finviz"):
    scrapFinvizDatas(name, config, logger)
    loadMainIndex(name, config, logger)

#================================================================
if __name__ == "__main__":
    from sys import argv
    from os import sep as osSep

    name = __file__.split(osSep)[-1:][0][:-3]
    configStr = "analyst"

    if len(argv) == 2: name = argv[1]
    name = name.lower()


    config, logger = init_logger(name=name, config="analyst")
    scrapFinvizDatas(name, config, logger)
    loadMainIndex(name, config, logger)
