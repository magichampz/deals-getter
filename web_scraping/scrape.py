import requests
import re
import pandas as pd
import numpy as np
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
import time
from utils.chopeDetails import parseTags
from utils.addressConverter import getLongLatFromRawAddress, countPostalCodesFromRawAddress

def get_webscrape_data():
    ## selenium used to scroll to the bottom of the page
    options = Options()
    options.add_argument("--headless")
    driver = webdriver.Chrome(options=options)

    driver.get("https://shop.chope.co/collections/best-sellers")

    SCROLL_PAUSE_TIME = 0.5

    # Get the height of the page
    last_height = driver.execute_script("return document.body.scrollHeight")

    while True:
        # Scroll to the bottom of the page
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")

        time.sleep(SCROLL_PAUSE_TIME)

        # Calculate new height and check if we have reached the end of the page
        new_height = driver.execute_script("return document.body.scrollHeight")
        if new_height == last_height:
            break
        
        last_height = new_height

    page_source = driver.page_source
    soup = BeautifulSoup(page_source, 'html.parser')

    # getting the relevant data
    all_deals = soup.find(id = 'bc-sf-filter-products')
    url = 'https://shop.chope.co'
    promos = []

    for deal in all_deals:
        title = getPromoTitle(deal)
        link = getPromoLink(deal)
        
        deal_link = url+link
        deal_page = requests.get(deal_link)
        deal_soup = BeautifulSoup(deal_page.content, 'html.parser')
        info = getPromoInfo(deal_soup)
        
        cur_deal_vouchers = getPromoVouchers(deal_soup)

        addressesAndOpeningHours = getPromoAddressAndOpeningHours(deal_soup)

        tagsList = getPromoTags(deal_soup)        
        image_url = getPromoImageUrl(deal)

        appendPromoGivenData(promos, title, info, addressesAndOpeningHours, image_url, tagsList, cur_deal_vouchers, deal_link)
    
        promos_adjusted = apply_offsets(promos)
    
    # return promos
    return promos_adjusted

def offset_range(count):
    # print(count)
    min_offset = -0.0006  # Minimum offset (negative)
    max_offset = 0.0006   # Maximum offset (positive)
    return np.random.uniform(min_offset, max_offset) * (count/5)

def convert_coordinates(coord_str, type):
    try:
        longitude, latitude = map(type, coord_str)
        return (longitude, latitude)
    except (ValueError, TypeError):
        return None

def apply_offsets(promos_og):
    df = pd.DataFrame(promos_og)
    
    # unpack tuple out of list in longlat column
    df['longlat'] = df['longlat'].apply(lambda x : x[0] if len(x)>0 else ('0.','0.')) 
    
    # convert longlat from tuple of strings to tuple of floats (specify type)
    df['longlat'] = df['longlat'].apply(convert_coordinates, type = float)
    
    # adding a column for the number of repetitions for a particular coordinate
    df['coord_count'] = df.groupby(['longlat'])['longlat'].transform('count')
    
    # use coord count to apply an offset in an appropriate range
    
    df['longlat'] = df.apply(lambda row: (
        row['longlat'][0] + offset_range(row['coord_count']),
        row['longlat'][1] + offset_range(row['coord_count'])
    ) if row['coord_count'] > 1 else row['longlat'], axis=1)
    
    # drop the extra column
    df.drop('coord_count', axis=1, inplace=True)
    
    # convert back from tuple of floats to tuple ofstrings
    df['longlat'] = df['longlat'].apply(convert_coordinates, type = str) 
    
    #  put tuple inside a list like the original dataframe
    df['longlat'] = df['longlat'].apply(lambda x : [x]) 
    
    # convert the df back into a list of dicts like the original promos format
    promos_mod = df.to_dict(orient = 'records')
    
    return promos_mod

def getPromoTitle(deal):
    return deal.select('a.color-blue.app-link')[0].text # restaurant / name of deal

def getPromoLink(deal):
    links = deal.select('a')
    link = links[0].get('href') # get url to go to the deal page
    return link

def getPromoInfo(deal_soup):
    infos = deal_soup.select('div.product-desc')
    info = infos[0].select('strong')[0].text #brief info on deal
    return info

def getPromoVouchers(deal_soup):
    # Get voucher details
    vouchers_div = deal_soup.select('div.product-variants.hide-mobile li.child.relative')
    cur_deal_vouchers = []
    for voucher in vouchers_div:
        # Extracting date
        date = voucher.select_one('div.date.color-blue.body-s.bold-700')
        if date:
            date = date.text.strip()

        # Extracting time
        time_ = voucher.select_one('div.time.body-s.color-darkgrey.mb-5')
        if time_:
            time_ = time_.text.strip()

        # Extracting price (both discounted and original)
        price_discounted = voucher.select_one('div.product-price strong.price.color-orange')
        if price_discounted:
            price_discounted = price_discounted.text.strip()
        
        price_original = voucher.select_one('div.product-price strike.color-darkgrey.body-s')
        if price_original:
            price_original = price_original.text.strip()

        product_savings = voucher.select_one('div.child-right div.product-savings.big')
        if product_savings:
            product_savings = product_savings.text.strip()

        cur_voucher = {"date": date, "time": time_, "price_discounted": price_discounted, "price_original": price_original, "product_savings": product_savings}
        cur_deal_vouchers.append(cur_voucher)
    return cur_deal_vouchers

def getPromoImageUrl(deal):
    image_tag = deal.select_one('.product-each-tile-image img')
    image_url = None
    if image_tag:
        image_url = image_tag['src']
    return image_url

def getPromoTags(deal_soup):
    cards = deal_soup.select('div.details')
    for card in cards:
        header = card.select('h5.header-xs.color-blue')
        
        if header == []:
            continue
        
        if header[0].text == "Cuisine":
            cuisine_div = card.select_one('div.rte')
            if cuisine_div:
                tags_unparsed = cuisine_div.text
                tagsList = parseTags(tags_unparsed)
                return tagsList

def getPromoAddressAndOpeningHours(deal_soup):
    """Returns a list of lists of addresses and opening hours for each outlet of the deal
    Returns:
        list: list of [address, opening_hours] for each outlet of the deal, where address is a string and opening_hours is a string
    """
    # Deal has multiple outlets
    if checkIfPromoHasMultipleOutlets(deal_soup):
        return getMultiOutletAddressAndOpeningHours(deal_soup)
    # Deal has one outlet/ address
    else:
        return getSingleOutletAddressAndOpeningHours(deal_soup)

def getMultiOutletAddressAndOpeningHours(deal_soup):
    concatenatedAddressAndOpeningHours = ""
    cards = deal_soup.select('div.details')
    for card in cards:
        header = card.select('h5.header-xs.color-blue')
        if header == []:
            continue
        if header[0].text == "Address":
            address_div = card.select_one('div.rte')
            if address_div:
                for br in address_div.find_all("br"):
                    br.replace_with(" ")  # Replace <br> with a space

                for p_tag in address_div.select('p'):
                    # Keep the <strong> tags by getting the HTML content of p_tag
                    p_html_content = p_tag.encode_contents().decode('utf-8')
                    concatenatedAddressAndOpeningHours += p_html_content + " "
    return parse_addresses_and_hours(concatenatedAddressAndOpeningHours)

# def parse_addresses_and_hours(input_str):
#     # Split the input string based on <strong> tags
#     parts = re.split(r'<strong>[^<]+</strong>', input_str)
#     parts = [part.strip() for part in parts if part.strip()]  # Remove empty or whitespace-only strings
    
#     results = []
    
#     for part in parts:
#         # Find the postal code (format: Singapore (******))
#         postal_code_match = re.search(r'Singapore \(\d{6}\)', part)
#         if postal_code_match:
#             postal_code_end = postal_code_match.end()
            
#             # Extract the address and opening hours
#             address = part[:postal_code_end].strip()
#             opening_hours = part[postal_code_end:].strip()
            
#             results.append([address, opening_hours])
    
#     return results

def parse_addresses_and_hours(input_str):
    if "<strong>" not in input_str:
        # Regular expression pattern to match each address and its opening hours
        pattern = r'([a-zA-Z0-9\s\-\#\,]+Singapore \(\d{6}\)) (Mon(?:-[^:]+)?: [^ ]+(?: [^ ]+)?(?:, )?)*(?:Sat(?:-[^:]+)?: [^ ]+(?: [^ ]+)?(?:, )?)*(?:Sun(?:-[^:]+)?: [^ ]+(?: [^ ]+)?(?:, )?)?'
        
        # Find all matches using the regular expression pattern
        matches = re.findall(pattern, input_str)
        
        # Initialize an empty list to store the results
        results = []
        
        # Loop through each match to extract the address and opening hours
        for match in matches:
            address, opening_hours = match
            results.append((address.strip(), opening_hours.strip()))
        
        return results
    
    # Split the input string based on <strong> tags, but keep the text within the tags
    parts = re.split(r'(<strong>[^<]+</strong>)', input_str)
    parts = [part.strip() for part in parts if part.strip()]  # Remove empty or whitespace-only strings
    
    results = []
    
    for i in range(0, len(parts), 2):
        strong_text = parts[i]  # Text within <strong> tags
        part = parts[i + 1]  # The address and opening hours part
        
        # Find the postal code (format: Singapore (******))
        postal_code_match = re.search(r'Singapore \(\d{6}\)', part)
        if postal_code_match:
            postal_code_end = postal_code_match.end()
            
            # Extract the address and opening hours
            address = strong_text + " " + part[:postal_code_end].strip()
            opening_hours = part[postal_code_end:].strip()
            
            results.append([address, opening_hours])
    
    return results

def getSingleOutletAddressAndOpeningHours(deal_soup):
    cards = deal_soup.select('div.details')
    address = None
    opening_hours = None
    for card in cards:
        header = card.select('h5.header-xs.color-blue')
        
        if header == []:
            continue

        if header[0].text == "Address":
            address = str(card.select('p')[0])
            address = strip_things(address)  # address of restaurant
        
        if header[0].text == "Opening Hours":
            opening_hours_div = card.select_one('div.rte')
            if opening_hours_div:
                opening_hours = opening_hours_div.text.replace("\n", "")
    if opening_hours == None:
        # There are 2 ways, from the given scraped data. If there are more new ways to format then these 2 way will not suffice
        # if parse_addresses_and_hours(address)[0][1] != '':
        #     return parse_addresses_and_hours(address)
        address_div = card.select_one('div.rte')
        if address_div:
            for br in address_div.find_all("br"):
                br.replace_with(" ")  # Replace <br> with a space
            concatenatedAddressAndOpeningHours = ""
            for p_tag in address_div.select('p'):
                # Keep the <strong> tags by getting the HTML content of p_tag
                p_html_content = p_tag.encode_contents().decode('utf-8')
                concatenatedAddressAndOpeningHours += p_html_content + " "
            return parse_addresses_and_hours(concatenatedAddressAndOpeningHours)
    return [[address, opening_hours]]

def checkIfPromoHasMultipleOutlets(deal_soup):
    cards = deal_soup.select('div.details')
    for card in cards:
        header = card.select('h5.header-xs.color-blue')
        if header == []:
            continue
        if header[0].text == "Address":
            # Check if there are multiple addresses, if there are multiple <p> tags
            address_div = card.select_one('div.rte')
            if address_div:
                totalPostalCodes = 0
                for p_tag in address_div.select('p'):
                    totalPostalCodes += countPostalCodesFromRawAddress(p_tag.text)
                return totalPostalCodes > 1
    print("Reached default return while checking mulitple outlets")
    return False


def appendPromoGivenData(promos, title, info, addressesAndOpeningHours, image_url, tagsList, cur_deal_vouchers, deal_link):
    if len(addressesAndOpeningHours) == 1:
        address, opening_hours = addressesAndOpeningHours[0]
        promos.append({
            "title": title,
            "info": info,
            "address": address,
            "image": image_url,
            "opening_hours": opening_hours,
            "tags": tagsList,
            "vouchers": cur_deal_vouchers,
            "link": deal_link,
            "longlat": getLongLatFromRawAddress(address),
            "id": len(promos)
        })
    else:
        for address, opening_hours in addressesAndOpeningHours:
            promos.append({
                "title": title,
                "info": info,
                "address": strip_things(address),
                "image": image_url,
                "opening_hours": opening_hours,
                "tags": tagsList,
                "vouchers": cur_deal_vouchers,
                "link": deal_link,
                "longlat": getLongLatFromRawAddress(address),
                "id": len(promos)
            })

def strip_things(string):
        output = string.replace("<p>",' ')
        output = output.replace("</p>",' ')
        output = output.replace("<br/>"," ")
        output = output.replace("<strong>","")
        output = output.replace("</strong>","")
        return output