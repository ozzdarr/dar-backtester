import re
import csv

#TODO open csv
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

def parseIB(reader_IB, headlines1):
    #TODO 21.7 and above
    ibRawList = list()
    headlines = next(reader_IB)
    print(headlines)
    for row in reader_IB:
        thisDict = dict()
        for i in range(0, len(headlines)):
            thisDict[headlines[i]] = row[i]

        ibRawList.append(thisDict)
    print(ibRawList)
    symList = list() #lists of symbols i've encountered twice in a certain date
    ibParsedList = list()
    for i in range(0, len(ibRawList)):
        currentRow = ibRawList[i]
        if currentRow['Symbol'] in symList:
            symList.remove(currentRow['Symbol'])
            continue
        for j in range(i+1, len(ibRawList)):
            if (ibRawList[j]['Symbol'] == currentRow['Symbol']) and (ibRawList[j]['TradeDate'] == currentRow['TradeDate']):
                symList.append(currentRow['Symbol'])
                currentSymDict = {'hintTime': currentRow['OrdrerTime'], 'symbol': currentRow['Symbol'], 'hintTrigger': 0,
                                  'hintStop': 0, 'entryTime': currentRow['TradeDate'] + " " + currentRow['TradeTime'],
                                  'entryPrice': currentRow['TradePrice'], 'exitTime': ibRawList[j]['TradeTime'],
                                  'exitPrice': ibRawList[j]['TradePrice'], 'revenue': ibRawList[j]['FifoPnlRealized'],
                                  'slippage': 0, 'comment': 0, 'hintDirection': getHintDirection(currentRow)}

                ibParsedList.append(currentSymDict)
                break

    print(ibParsedList)

    return ibParsedList

def getHintDirection(currentRow):
    print(currentRow['Buy/Sell'])
    if currentRow['Buy/Sell'] == 'BUY':
        return 'long'
    else:
        return 'short'


def parseBacklog(reader_BT):
    headlines = next(reader_BT)
    backlogList = list()
    for headline in headlines: #TODO del this
        print(headline)

    for row in reader_BT:
        thisDict = dict()
        for i in range(0, len(headlines)):
            thisDict[headlines[i]] = row[i]

        backlogList.append(thisDict)
        thisDict['revenue'] *= 200
    #print(backlogList)

    return headlines, backlogList

def main():
    f1 = open('iblog.csv', newline='')
    f2 = open('backlog.csv', newline='')
    reader_IB = csv.reader(f1)
    reader_BT = csv.reader(f2)

    HEADLINES = list() #TODO make global

    HEADLINES, backlogList = parseBacklog(reader_BT)
    print("headlinesTest")
    print(HEADLINES)
    print("/headlinesTest")
    ibPasedList = parseIB(reader_IB, HEADLINES)
    print("#@$%$#%#%$$#%#$%")
    print(ibPasedList)
    print("#$%$#%$#%$#%$#%$")
    resultFile = open("IBOutput.csv", 'w')
    wr = csv.DictWriter(resultFile, CSV_KEYS, dialect='excel')
    wr.writeheader()
    wr.writerows(ibPasedList)


main()