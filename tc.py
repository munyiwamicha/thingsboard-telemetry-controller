import sys, csv, requests, json, os, inspect, time, pprint
from datetime import datetime
from time import strftime, localtime
from openpyxl import Workbook
import argparse, ast, math, queue, threading

# Get Folder Path
FolderPath = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))

# Create a pretty printer object
pp = pprint.PrettyPrinter(indent=4)

##### Constants #####
# Entity Types
TENANT = 'TENANT'
CUSTOMER = 'CUSTOMER'
USER = 'USER'
DASHBOARD = 'DASHBOARD'
ASSET = 'ASSET'
DEVICE = 'DEVICE'
ALARM = 'ALARM'

# Formats
XLSX = 'XLSX'
CSV = 'CSV'

#Aggregation modes
AVG = 'AVG'
MIN = 'MIN'
MAX = 'MAX'
NONE = 'NONE'
SUM = 'SUM'
COUNT = 'COUNT'

#keyList Mode
ALL = "ALL"

# Main Function
def main(args):
    try:
        mode = args.mode
        entity_type = args.entity_type
        entity_id = args.entity_id
        startTs = args.startTs
        endTs = args.endTs
        Interval = args.interval*1000
        isTelemetry = args.isTelemetry
        Limit = args.limit
        Agg = args.agg
        Format = args.format
        keyList = args.keyList.split(',')
    except:
        #raise
        pass

    if(mode == "getRequestID"):
        getRequestID()
    elif(mode == "getToken"):
        getToken()
    elif mode == "getKeyList":
        getKeyList(entity_type, entity_id,isTelemetry)
    elif mode == "getLatestValue":
        getLatestValue(entity_type, entity_id)
    elif mode == "exportLog":
        exportLog(entity_type, entity_id, keyList, startTs, endTs, Interval, isTelemetry, Limit, Agg, Format)
    else:
        raise ValueError("Unimplemented mode")

#Convert Timestamp unix to datetime
def UNIXtoDatetime(unix_ts):
    return datetime.fromtimestamp(unix_ts/1000).strftime("%Y-%m-%d %H:%M:%S")

#Function to get Request ID
def getRequestID():
    with open(FolderPath + "/requestID.txt", "r") as file:
        data = ast.literal_eval(file.readline())
        prevTs = data[0]
        prevID = data[1]

    if prevID >= 100:
        newID = 1
    else:
        newID = prevID + 1

    currentTs = time.time()
    
    if (currentTs - prevTs) >= 86400:
        newdata = [currentTs,newID]
        os.system('sudo rm ExportResult/*')
    else:
        newdata = [prevTs,newID]

    with open(FolderPath + "/requestID.txt", "w") as file:
        file.write(str(newdata))
        
    return newID

# Function to get JWT_Token
def getToken():
    url = 'https://manage.pulse.ke/api/auth/login'
    headers = {'Content-Type': 'application/json', 'Accept': 'application/json'}
    loginJSON = {'username': 'joseph.kagicha@gmail.com', 'password': 'don84#aq21'}
    # joseph.kagicha@gmail.com don84#aq21
    #{'username': 'stephen@paainfra.co', 'password': 'i7HMhXv3fT5f4A'}
    tokenAuthResp = requests.post(url, headers=headers, json=loginJSON).json()
    token = tokenAuthResp['token']
    
    #Return token in string format
    return token

# Function to Get All (Arrtibute/Telemetry) Variable Name in Device
def getKeyList(entity_type, entity_id, isTelemetry=True):
    # Args:
    # - entity_type   : DEVICE, ASSET, OR ETC
    # - entity_id     : ID of the entity
    # Return:
    # - KeyList          : List of variable name

    JWT_Token = getToken()
    if isTelemetry:
        url = 'https://manage.pulse.ke/api/plugins/telemetry/%s/%s/keys/timeseries' %(entity_type,entity_id)
    else:
        url = 'https://manage.pulse.ke/api/plugins/telemetry/%s/%s/keys/attributes' %(entity_type,entity_id)
    headers = {'Accept':'application/json', 'X-Authorization': "Bearer "+JWT_Token}
    KeyList = requests.get(url, headers=headers, json=None).json()
    
    return KeyList

# Function to Get Latest Variable Value in Device
def getLatestValue(entity_type, entity_id, isTelemetry=True,keyList=ALL):
    # Args:
    # - entity_type   : DEVICE, ASSET, OR ETC
    # - entity_id     : ID of the entity
    # Return:
    # - LatestValue   : Dictionary of variable names and their latest value

    JWT_Token = getToken()
    if isTelemetry:
        url = 'https://manage.pulse.ke/api/plugins/telemetry/%s/%s/values/timeseries?keys=' %(entity_type,entity_id)
    else:
        url = 'https://manage.pulse.ke/api/plugins/telemetry/%s/%s/values/attributes?keys=' %(entity_type,entity_id)

    if keyList==ALL :
        keys=getKeyList(entity_type, entity_id, isTelemetry)
    else:
        keys=keyList
        
    for i,key in enumerate(keys):
        if i != len(keys)-1:
            url += key + ','
        else:
            url += key + '&'

    headers = {'Accept':'application/json', 'X-Authorization': "Bearer "+JWT_Token}
    LatestValue = requests.get(url, headers=headers, json=None).json()

    #Remove timestamp and extract values
    for key in keys:
        LatestValue[key]=ast.literal_eval(LatestValue[key][0]['value'])
    
    return LatestValue

def LogQuery(entity_type, entity_id, keyList, startTs, endTs, Interval = 60, isTelemetry=True, limit=500, Agg=NONE):
    try:
        JWT_Token = getToken()

        if isTelemetry:
            url = 'https://manage.pulse.ke/api/plugins/telemetry/%s/%s/values/timeseries?keys=' %(entity_type,entity_id)        
        else:
            url = 'https://manage.pulse.ke/api/plugins/attributes/%s/%s/values/attributes?keys=' %(entity_type,entity_id)

        for i,key in enumerate(keyList):
            if i != len(keyList)-1:
                url += key + ','
            else:
                url += key + '&'

        url += 'startTs=%d&endTs=%d&interval=%d&' %(startTs, endTs, Interval)
        
        if limit != None:
            url += 'limit=%d&' %limit
        url += 'agg=%s' %Agg
        
        headers = {'Accept':'application/json', 'X-Authorization': "Bearer "+JWT_Token}
        Log_JSON = requests.get(url, headers=headers, json=None).json()
        #print(Log_JSON)
        
        if len(Log_JSON)!=0:
            var = list(Log_JSON.keys())
            val = list(Log_JSON.values())
                
            #Separate Timestamp and Variable Value
            tsList= []
            valList= []
            for i,subval in enumerate(val):
                for j, item in enumerate(subval):
                    subval[j]= list(subval[j].values())
                val[i] = list(map(list, zip(*val[i])))
                tsList.append(val[i][0])
                valList.append(val[i][1])

            #Check missing variables
            missVars = list(set(keyList)-set(var))
            missVarsIndex = [keyList.index(x) for x in missVars]

            if len(missVars) != 0:
                print("Missing Vars:", missVars )
                print("Missing Vars index:", missVarsIndex )

            for index in missVarsIndex:
                try:
                    tsList.insert(index,tsList[index-1])
                    valList.insert(index,['None']*len(tsList[index-1]))
                except:
                    tsList.insert(index,tsList[index])
                    valList.insert(index,['None']*len(tsList[index]))
                    
            _tsList = []
            #Combine all timestamp of each variable
            for i,item in enumerate(tsList):
                if i == 0:
                    _tsList += item
                else:
                    newTs = list(set(tsList[i])-set(_tsList))
                    _tsList +=newTs

            #Sort timestamp
            _tsList.sort()
            
            #Fill blank value in specific timestamp with None
            _valList = [None]*len(keyList)
            for i in range(0,len(keyList)):
                _valList[i]=['None']*len(_tsList)
                for j,item in enumerate(tsList[i]):
                    index = _tsList.index(item)
                    _valList[i][index]=valList[i][j]
            
            # Transpose Value Matrice
            Records = list(map(list, zip(*_valList)))
            
            #Ubah tipe data
            for row in Records:
                for i,item in enumerate(row):
                    try:
                        row[i]=ast.literal_eval(item)
                        row[i]=round(row[i],3)
                    except:
                        pass
        else:
            _tsList=[]
            Records=[]
        return [_tsList,Records]
    except Exception as e:
        #raise
        print(e)
        return -1

def LogCollecter(rowPart,colPart,ts,rec,*argv):
    Result = LogQuery(*argv)
    ts[rowPart][colPart]=Result[0]
    rec[rowPart][colPart]=Result[1]
    
# Function to Get Historical Value of Variables in Device in .csv or .xlsx format 
def exportLog(entity_type, entity_id, keyList, startTs, endTs, Interval = 60, isTelemetry=True, limit=500, Agg=NONE, Format=XLSX):
    # Args:
    # - entity_type     : DEVICE, ASSET, OR ETC
    # - entity_id       : ID of the entity
    # - keyList         : List of variable name
    # - startTs         : start timestamp
    # - endTs           : end timestamp
    # - Interval        : aggregation interval
    # - isTelemetry     : 1 for telemetry, 0 for attribute
    # - limit           : records limit
    # - Agg             : Aggregation mode
    # - Format          : Export file format
    # Return:
    # - Filename        : Filename with extension
    
    try:    
        t0 = time.time()

        #Get Request ID
        RequestID = getRequestID()
        
        #Key Partition (Columns)
        totalKey = len(keyList)
        totalKeyPart = math.ceil(totalKey/5)
        
        keys = []
        for i in range(0,totalKeyPart):
            try:
                keys.append(keyList[i*5:(i*5)+5])
            except:
                keys.append(keyList[i*5:])

        #Timestamp Partition (Rows)
        ts_list = list(range(startTs,endTs,604800000))+[endTs]
        totalTsPart = math.ceil((endTs-startTs)/604800000)

        #Initialization
        threads =[]
        _ts = []
        _rec = []
        for i in range(0,totalTsPart):
            threads.append([None]*totalKeyPart)
            _ts.append([None]*totalKeyPart)
            _rec.append([None]*totalKeyPart)

        #Start threads
        for i in range(0,len(ts_list)-1):
            _startTs = ts_list[i]
            _endTs = ts_list[i+1]
            for j in range(0,totalKeyPart):
                t = threading.Thread(target=LogCollecter, args=[i, j, _ts, _rec, entity_type, entity_id, keys[j], _startTs, _endTs, Interval, isTelemetry, limit, Agg])
                t.setDaemon(True)
                t.start()
                threads[i][j]=t
                
        #print(keys)
        
        # Join all the threads
        for i in range(0,totalTsPart):
            for j in range(0,totalKeyPart):
                threads[i][j].join()
        
        t1 = time.time()
        #print("query duration:", t1-t0, "s")

        #Combine all timestamp of each variable in different time partition
        ts = []
        for i in range(0,totalTsPart):
            ts.append([])
            for j in range(0,totalKeyPart):
                if len(ts[i]) == 0:
                    ts[i] += _ts[i][j]
                else:
                    newTs = list(set(_ts[i][j])-set(ts[i]))
                    ts[i] +=newTs
            #Sort timestamp
            ts[i].sort()

        #Combine all timestamp of all time partition
        ts_gen = []
        for i in range(0,totalTsPart):
            if len(ts_gen) == 0:
                ts_gen += ts[i]
            else:
                newTs = list(set(ts[i])-set(ts_gen))
                ts_gen += newTs
        
        #Sort general timestamp
        ts_gen.sort()

        #Fill blank value in specific timestamp with None
        rec_ = []
        for i in range(0,totalTsPart):
            rec_.append([None]*totalKeyPart)
            
        for i in range(0,totalTsPart):
            for j in range(0,totalKeyPart):
                rec_[i][j] = [[None]*len(keys[j])]*len(ts[i])
                for k,item in enumerate(_ts[i][j]):
                    index = ts[i].index(item)
                    try:
                        rec_[i][j][index]=_rec[i][j][k]
                    except:
                        print(i,j,index,k,item,_rec[i][j])
                    

        #Combine records from all timestamp partitions
        rec_allts = []*totalKeyPart
        for i in range(0,totalKeyPart):
            rec_allts.append([])
            for j in range(0,totalTsPart):
                rec_allts[i]+=rec_[j][i]
                
        #Combine records from all column partitions
        rec = []
        for i in range(0, len(ts_gen)):
            rec.append([])
            for j in range(0, totalKeyPart):
                rec[i]+=rec_allts[j][i]
        
        # Convert Timestamp (in UNIX ms) to string of Year-Month-Date Hour-Min-Secs Format
        for i,item in enumerate(ts_gen):
            ts_gen[i] = UNIXtoDatetime(item)
        
        # Add Timestamp to Records (This represents a row in Excel or CSV file)
        for i, item in enumerate(rec):
            rec[i].insert(0, ts_gen[i])
        
        t2 = time.time()
        #print("Processing duration:", t2-t1, "s")
        #print("Total duration:", t2-t0, "s")

        
        #Export Data Log into CSV or XLSX format
        Filename = "DataLog_" + datetime.fromtimestamp(startTs/1000).strftime("%Y-%m-%d") + "_sd_" + datetime.fromtimestamp(endTs/1000).strftime("%Y-%m-%d")+"_"+str(RequestID)
        if Format == CSV:
            with open(FolderPath + '/ExportResult/%s.csv' %Filename, mode='w') as file:
                file_writer = csv.writer(file, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)
                column = ['Timestamp']+ keyList
                file_writer.writerow(column)

                for i, item in enumerate(rec):
                    file_writer.writerow(item)
            print(FolderPath + '/ExportResult/%s.csv' %Filename)
            return FolderPath + '/ExportResult/%s.csv' %Filename
        
        else:      
            wb = Workbook()

            # grab the active worksheet
            ws = wb.active

            column = ['Timestamp']+ keyList
            ws.append(column)
            
            for i, item in enumerate(rec):
                ws.append(item)

            # Save the file
            wb.save(FolderPath + '/ExportResult/%s.xlsx' %Filename)
            print(FolderPath + '/ExportResult/%s.xlsx' %Filename)
            return FolderPath + '/ExportResult/%s.xlsx' %Filename
        
    except Exception as e:
        #print(e)
        #raise
        return -1

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", type=str, help="Telemetry controller API", default=None)
    parser.add_argument("--entity_type", type=str, help="type of the entity", default=DEVICE)
    parser.add_argument("--entity_id", type=str, help="ID of the entity", default=None)
    parser.add_argument("--keyList", type=str, help="List of variable name", default=None)
    parser.add_argument("--startTs", type=int, help="Start Timestamp in UNIX miliseconds", default=None)
    parser.add_argument("--endTs", type=int, help="End Timestamp in UNIX miliseconds", default=None)
    parser.add_argument("--interval", type=int, help="Aggregation interval in seconds", default=1200)
    parser.add_argument("--isTelemetry", type=bool, help="1 for telemetry, 0 for attributes", default=1)
    parser.add_argument("--limit", type=int, help="Records Limit", default=500)
    parser.add_argument("--agg", type=str, help="Aggregation Mode", default=AVG)
    parser.add_argument("--format", type=str, help="Log Export File Format", default=XLSX)
    
    args = parser.parse_args(sys.argv[1:]);
    
    main(args);



