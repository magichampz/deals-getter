import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
import time
from utils.chopeDetails import parseTags

def get_webscrape_data():
    ## selenium used to scroll to the bottom of the page
    options = Options()
    options.add_argument("--headless")
    driver = webdriver.Chrome(options=options)

    driver.get("https://shop.chope.co/collections/best-sellers")

    SCROLL_PAUSE_TIME = 2

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

    def strip_things(string):
        output = string.replace("<p>",'')
        output = output.replace("</p>",'')
        output = output.replace("<br/>",", ")
        return output
    i = 0
    for deal in all_deals:
        title = deal.select('a.color-blue.app-link') # restaurant / name of deal
        links = deal.select('a')
        link = links[0].get('href') # get url to go to the deal page
        
        deal_link = url+link
        deal_page = requests.get(deal_link)
        deal_soup = BeautifulSoup(deal_page.content, 'html.parser')
        infos = deal_soup.select('div.product-desc')
        info = infos[0].select('strong')[0].text #brief info on deal
        
        cards = deal_soup.select('div.details')
        # if i == 0:
        #     print(deal_soup)
        #     print("cards\n")
        #     print(cards)
        #     i += 1
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
                    opening_hours = opening_hours_div.text
            
            if header[0].text == "Cuisine":
                cuisine_div = card.select_one('div.rte')
                if cuisine_div:
                    tags_unparsed = cuisine_div.text
                    tagsList = parseTags(tags_unparsed)

        # get image        
        image_tag = deal.select_one('.product-each-tile-image img')
        image_url = None
        if image_tag:
            image_url = image_tag['src']
        promos.append({
            "title": title[0].text,
            "info": info,
            "address": address,
            "image": image_url,
            "opening_hours": opening_hours,
            "tags": tagsList
        })
    return promos

