import datetime, http.client
import xml.etree.ElementTree as ET
from zoneinfo import ZoneInfo

def lambda_handler(event, context):
    today = datetime.date.today()
    tomorrow = datetime.date.today() + datetime.timedelta(days=1)
    url_start = "/api?securityToken="
    key = YOUR_OWN_ENTSO_E_API_KEY
    url_middle = "&documentType=A44&processType=A01&in_Domain=10YFI-1--------U&out_Domain=10YFI-1--------U&periodStart="
    url_end = "&periodEnd="
    connection = http.client.HTTPSConnection("web-api.tp.entsoe.eu")
    connection.request("GET", url_start + key + url_middle + today.strftime("%Y%m%d") + "2300" + url_end + tomorrow.strftime("%Y%m%d") + "2300")
    response = connection.getresponse()
    if(response.status >= 400):
        print("HTTP Error", response.status)
        return
    
    responsestr = response.read().decode()
    
    root = ET.fromstring(responsestr)
    reason = root.find(".//{*}Reason")
    if (reason):
        print ("Request failed, reason code:",reason.find("{*}code").text)
        return
    
    for region in root.iterfind(".//{*}in_Domain.mRID"):
        print ("Region:", region.text)
        
    for currency in root.iterfind(".//{*}currency_Unit.name"):
        print ("Currency unit:", currency.text)
    
    for energyunit in root.iterfind(".//{*}price_Measure_Unit.name"):
        print ("Energy unit:", energyunit.text)
    
    resolution = datetime.timedelta(hours=1)

    pointlist = []
    
    for period in root.findall(".//{*}Period"):
        interval = period.find("{*}timeInterval")
        starttime = datetime.datetime.strptime(interval.find("{*}start").text,"%Y-%m-%dT%H:%MZ")
        print ("Period start (UTC):", starttime, starttime.tzname())
        resolutionstr = period.find("{*}resolution").text
        print ("Input time resolution:", resolutionstr)
        if (resolutionstr == "PT60M"):
            resolution = datetime.timedelta(minutes=60)
        if (resolutionstr == "PT30M"):
            resolution = datetime.timedelta(minutes=30)
        if (resolutionstr == "PT15M"):
            resolution = datetime.timedelta(minutes=15)
        if (resolutionstr == "P7D"):
            resolution = datetime.timedelta(days=7)
        print ("Time resolution:",resolution)
        for point in period.findall("{*}Point"):
            index = int (point.find("{*}position").text) - 1
            price = float (point.find("{*}price.amount").text)
            pointtime = starttime + (resolution*index)
            pointtime = pointtime.replace(tzinfo=datetime.timezone.utc)
            pointlist.append((price, pointtime))
           
    sortedpointlist = sorted(pointlist, key=lambda price: price[0])
    for index in range(len(sortedpointlist)):
        hinta =  round(sortedpointlist[index][0]*10)/100
        aika = sortedpointlist[index][1].astimezone(ZoneInfo("Europe/Helsinki"))
        aikastr = aika.strftime("%d.%m.%Y %H.%M")
        print ("Hinta snt/kWh:", hinta, "Aika:", aikastr)
