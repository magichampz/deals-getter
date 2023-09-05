import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
import time
from utils.chopeDetails import parseTags
from utils.addressConverter import getLongLatFromRawAddress

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

    def strip_things(string):
        output = string.replace("<p>",'')
        output = output.replace("</p>",'')
        output = output.replace("<br/>",", ")
        return output

    id = 0
    for deal in all_deals:
        title = deal.select('a.color-blue.app-link') # restaurant / name of deal
        links = deal.select('a')
        link = links[0].get('href') # get url to go to the deal page
        
        deal_link = url+link
        deal_page = requests.get(deal_link)
        deal_soup = BeautifulSoup(deal_page.content, 'html.parser')
        infos = deal_soup.select('div.product-desc')
        info = infos[0].select('strong')[0].text #brief info on deal
        
        # Get voucher details
        vouchers_div = deal_soup.select('div.product-variants.hide-mobile li.child.relative')#deal_soup.select('div.product-variants.hide-mobile')
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

        cards = deal_soup.select('div.details')

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
            "tags": tagsList,
            "vouchers": cur_deal_vouchers,
            "link": deal_link,
            "longlat": getLongLatFromRawAddress(address),
            "id": id
        })
        id += 1
    return promos

