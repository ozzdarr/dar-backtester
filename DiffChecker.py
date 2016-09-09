import re
import csv
from datetime import datetime as dt
from datetime import time
from datetime import timedelta
import time

CSV_KEYS = [
    "hintTime",
    "symbol",
    "hintTrigger",
    "hintDirection",
    "hintStop",
    "entryTime",
    "entryPrice",
    "exitTime",
    "exitPrice",
    "revenue",
    "slippage",
    "comment"
]
DIFF_KEYS = [
    'source',
    "hintTime",
    "symbol",
    "hintTrigger",
    "hintDirection",
    "hintStop",
    "entryTime",
    "entryPrice",
    "exitTime",
    "exitPrice",
    "revenue",
    "slippage",
    "comment"
]


def parseIB(reader_IB, headlines1):
    # TODO dar try to remove headlines1 from the signature (didn't want to mess your work)
    """Opens original IB log and parses it into BT log format"""
    #TODO 21.7 and above
    barrageDate = dt.strptime("21/07/2016", "%d/%m/%Y")

    ibRawList = list()
    headlines = next(reader_IB)

    for row in reader_IB:
        thisDict = dict()
        for i in range(0, len(headlines)):
            thisDict[headlines[i]] = row[i]

        ibRawList.append(thisDict)

    symList = list()  # lists of symbols i've encountered twice in a certain date
    ibParsedList = list()
    for i in range(0, len(ibRawList)):
        currentRow = ibRawList[i]
        if currentRow['Symbol'] in symList:
            symList.remove(currentRow['Symbol'])
            continue

        for j in range(i+1, len(ibRawList)):
            if (ibRawList[j]['Symbol'] == currentRow['Symbol']) and (ibRawList[j]['TradeDate'] == currentRow['TradeDate']):
                symList.append(currentRow['Symbol'])
                currentSymDict = {'source': 'IB',
                                  'hintTime': currentRow['TradeDate'] + " " + currentRow['OrderTime'],
                                  'symbol': currentRow['Symbol'],
                                  'hintTrigger': 0,
                                  'hintStop': 0,
                                  'entryTime': currentRow['TradeDate'] + " " + currentRow['TradeTime'],
                                  'entryPrice': currentRow['TradePrice'],
                                  'exitTime': ibRawList[j]['TradeDate'] + " " + ibRawList[j]['TradeTime'],
                                  'exitPrice': ibRawList[j]['TradePrice'],
                                  'revenue': ibRawList[j]['FifoPnlRealized'],
                                  'slippage': 0,
                                  'comment': 0,
                                  'hintDirection': getHintDirection(currentRow)
                                  }

                ibParsedList.append(currentSymDict)
                break

    for ibHint in ibParsedList:
        ibHint['entryTime'] = (dt.strptime(ibHint['entryTime'], "%d/%m/%Y %H:%M:%S")) + timedelta(hours=4)
        ibHint['exitTime'] = (dt.strptime(ibHint['exitTime'], "%d/%m/%Y %H:%M:%S")) + timedelta(hours=4)
        ibHint['hintTime'] = (dt.strptime(ibHint['hintTime'], "%d/%m/%Y %H:%M:%S")) + timedelta(hours=4)

    return ibParsedList


def getHintDirection(currentRow):
    if currentRow['Buy/Sell'] == 'BUY':

        return 'long'

    else:

        return 'short'


def parseBacklog(reader_BT):
    headlines = next(reader_BT)
    backlogList = list()

    for row in reader_BT:
        thisDict = dict()
        for i in range(0, len(headlines)):
            thisDict[headlines[i]] = row[i]
            thisDict['source'] = 'BT'

        backlogList.append(thisDict)

    for btHint in backlogList:
        btHint['hintTime'] = dt.strptime(btHint['hintTime'], "%d/%m/%Y %H:%M:%S")
        if btHint['entryTime'] not in ['did not enter','cancel','no bars']:
            btHint['entryTime'] = dt.strptime(btHint['entryTime'], "%d/%m/%Y %H:%M:%S")
            btHint['exitTime'] = dt.strptime(btHint['exitTime'], "%d/%m/%Y %H:%M:%S")
        if btHint['revenue'] not in ['did not enter','cancel','no bars']:
            btHint['revenue'] = float(btHint['revenue']) * 200

    return headlines, backlogList


def diff(ib, bt):
    # TODO dar - document this plz
    hints_diff = list()

    for btHint in bt:
        match_hint = None
        # append hint for the new diff file
        hints_diff.append(btHint)
        for ibHint in ib:
            delta = (btHint['hintTime'] - ibHint['hintTime'])
            # Check if the hint exists in ib log
            if (btHint['hintTime'].date() == ibHint['hintTime'].date()) and (btHint['symbol'] == ibHint['symbol']) and timedelta(
                    minutes=10) > delta > timedelta(days=-1, minutes=1430):
                if ibHint['symbol'] == 'YY':
                    print(ibHint)
                    print(btHint)
                    print(btHint['hintTime'] - ibHint['hintTime'])
                    print(timedelta(days=-1,minutes=1438))

                match_hint = ibHint
                if btHint['entryTime'] in ['did not enter', 'cancel', 'no bars']:
                    btHint['comment'] = btHint['comment'] = str(btHint['comment']) + ' ,Bot has entered position while backtester did not'
                    hints_diff.append(ibHint)
                    break

                # compare...
                if (btHint['entryTime'] - ibHint['entryTime']) > timedelta(minutes=2) or (btHint['entryTime'] - ibHint['entryTime']) < timedelta(days=-1,minutes=1438) :
                    print(btHint['entryTime'] - ibHint['entryTime'])
                    btHint['comment'] = str(btHint['comment']) + ' ,Difference in entry time: ' + str(ibHint['entryTime'] - (btHint['entryTime']))

                if (float(btHint['entryPrice']) - float(ibHint['entryPrice'])) > 0.05:
                    btHint['comment'] = str(btHint['comment']) + ' ,Difference in entry price: ' + str(float(btHint['entryPrice']) - float(ibHint['entryPrice']))

                if (btHint['exitTime'] - ibHint['exitTime']) > timedelta(minutes=6) or (btHint['exitTime'] - ibHint['exitTime']) < timedelta(days=-1,minutes=1434):
                    btHint['comment'] = str(btHint['comment']) + ' ,Difference in exit time:' + str((btHint['exitTime'] - ibHint['exitTime']))

                if (float(btHint['exitPrice']) - float(ibHint['exitPrice'])) > 0.05:
                    btHint['comment'] = str(btHint['comment']) + ' ,Difference in exit price:' + str(float(btHint['exitPrice']) - float(ibHint['exitPrice']))

                # append the  ib matched hint after the bt hint
                ibHint['comment'] = str(ibHint['comment']) + ' ,Latency in order time - ' + str((ibHint['hintTime'] - btHint['hintTime']))
                print(ibHint)
                hints_diff.append(ibHint)

        # Bot did not entered while BT did entered
        if not match_hint and (btHint['entryTime'] not in ['did not enter', 'cancel', 'no bars']) :
            btHint['comment'] = str(btHint['comment']) + ' ,Bot did not entered while BT did entered'

    # Check if there are hints that was executed by bot but not by BT
    for ibHint in ib:
        match_hint = None
        for btHint in bt:
            delta = (btHint['hintTime'] - ibHint['hintTime'])
            if (btHint['hintTime'].date() == ibHint['hintTime'].date()) and (btHint['symbol'] == ibHint['symbol']) and timedelta(
                    minutes=10) > delta > timedelta(days=-1, minutes=1430):
                match_hint = ibHint

        if not match_hint:
            ibHint['comment'] =  str(ibHint['comment']) + ' ,hint was executed by bot, but not by BT'
            hints_diff.append(ibHint)

    return hints_diff


def main():
    f1 = open('iblog.csv', newline='')
    f2 = open('backlog.csv', newline='')
    reader_IB = csv.reader(f1)
    reader_BT = csv.reader(f2)

    HEADLINES = list() #TODO make global

    HEADLINES, backlogList = parseBacklog(reader_BT)
    ibparsedList = parseIB(reader_IB, HEADLINES)

    diff_list = diff(ibparsedList,backlogList)

    diffFile = open("Diff.csv", 'w')
    wr = csv.DictWriter(diffFile, DIFF_KEYS, dialect='excel')
    wr.writeheader()
    wr.writerows(diff_list)

    resultFile = open("IBOutput.csv", 'w')
    wr = csv.DictWriter(resultFile, DIFF_KEYS, dialect='excel')
    wr.writeheader()
    wr.writerows(ibparsedList)

main()
