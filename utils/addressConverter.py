import requests
import json

def getLongLatFromRawAddress(fullAddress):
        postalCodes = []

        for i in range(len(fullAddress)):
            if fullAddress[i] == ')' and i - len("Singapore (123456") >= 0:
                   if fullAddress[i - len("Singapore (123456"): i - len("Singapore (123456") + len("Singapore (")] == "Singapore (":
                    postalCodes.append(fullAddress[i - len("123456"): i])
        
        longLats = []
        for postal in postalCodes:
              longLats.append(getLongLatFromPostal(postal))
        return longLats
                

def getLongLatFromPostal(postal):
        url = f"https://www.onemap.gov.sg/api/common/elastic/search?searchVal={postal}&returnGeom=Y&getAddrDetails=Y&pageNum=1"
        headers = {"Authorization": "**********************"}
        response = requests.request("GET", url, headers=headers)
        # Parse the response text into a dictionary
        data = json.loads(response.text)

        if data['found'] == 0:
             print("Invalid postal given")
             return (-1, -1)
        
        # Access the latitude and longitude from the dictionary
        latitude = data['results'][0]['LATITUDE']
        longitude = data['results'][0]['LONGITUDE']
        building_name = data['results'][0]['BUILDING']
        print(f"Queried for: {building_name}")

        return longitude, latitude

if __name__ == "__main__":
    pass