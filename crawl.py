# -*- coding: utf-8 -*-
"""
Simple crawler to interate through company's data so I see how complete it is (and therefore how useful it is. I intend to make updates where there are gaps and provide this info back to techireland

@author: kdwalsh based on idwaker's linkedin version

Requirements:
    python-selenium
    python-click
    python-keyring
    lxml

Tested on Python 3 not sure how Python 2 behaves
"""

import sys
import csv
import time
import click
import getpass
import keyring
from selenium import webdriver
from selenium.common.exceptions import (WebDriverException, NoSuchElementException)
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import re
import random
import lxml.html
import pandas as pd

class UnknownUserException(Exception):
    pass


class UnknownBrowserException(Exception):
    pass


class WebBus:
    """
    context manager to handle webdriver part
    """

    def __init__(self, browser):
        self.browser = browser
        self.driver = None

    def __enter__(self):
        # XXX: This is not so elegant
        # should be written in better way
        if self.browser.lower() == 'firefox':
            self.driver = webdriver.Firefox()
        elif self.browser.lower() == 'chrome':
            self.driver = webdriver.Chrome()
        elif self.browser.lower() == 'phantomjs':
            self.driver = webdriver.PhantomJS()
        else:
            raise UnknownBrowserException("Unknown Browser")

        return self

    def __exit__(self, _type, value, traceback):
        if _type is OSError or _type is WebDriverException:
            click.echo("Please make sure you have this browser")
            return False
        if _type is UnknownBrowserException:
            click.echo("Please use either Firefox, PhantomJS or Chrome")
            return False
        print('__exit__, driver close')
        self.driver.close()

def collect_urls(filepath):
    """
    collect urls from the file given
    """
    items = {}
    headers = {}

    df = pd.read_csv(filepath)
    items = df["Company URL"] #you can also use df['column_name']

    return items

@click.group()
def cli():
    pass

@click.command()
@click.option('--browser', default='phantomjs', help='Browser to run with')
@click.argument('infile')
@click.argument('outfile')                        
def crawlcompanies(browser, infile, outfile):
    """
    Run this crawler with specified username
    """

    # first check and read the input file
    links = collect_urls(infile)   #get urls from file - could make a single smarter file reader proc
    
    fieldnames = ['Name', 'Source', 'URL', 'Founder URL', 'Press URL', 'Founders', 'Female Founder', 'Employees', 'Founded Year',
                      'Sector', 'Company Stage', 'Product Stage',
                      'Irish Headquarters', 'Target Markets', 'International Offices', 'Business Model',
                      'Total Funding', 'Latest Funding', 'Acquired by',
                      "We're looking for", 'Directors']
    # then check we can write the output file
    # we don't want to complete process and show error about not
    # able to write outputs

    with open(outfile, 'w', newline='') as csvfile:
        # just write headers now
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()


    # now open the browser
    with open(outfile, 'a+', newline='') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

        with WebBus(browser) as bus:
            # print('Starting writer')
            for link in links:
                profiles = []
                valueData = []
                titleData = []
                data = []
                line = {}
                # every search result
                print('link:',link)
                
                bus.driver.get(link)
                time.sleep(random.uniform(0.1, 0.5))
                try:
                    websiteButton = bus.driver.find_element_by_class_name('website-link-outer')
                    website = websiteButton.find_element_by_css_selector('a').get_attribute("href")
                    line['URL'] = website
##                    print('URL: ', website)
                except NoSuchElementException:
                    print('No website found')
                    try:
                        socialLinks = bus.driver.find_element_by_class_name('social-links')
                        socials = socialLinks.find_elements_by_css_selector('a')
                        socialLink = ''
                        for social in socials:
                            if socialLink != '':
                                socialLink = socialLink + '; ' + social.get_attribute("href")
                            else:
                                socialLink = social.get_attribute("href")
                            print(socialLink)
                            line['URL'] = socialLink
                        print('Social media page: ', socialLink)
                    except NoSuchElementException:
                        print('And no social media page listed')
##                        continue                        
##                    continue                        

                name = bus.driver.find_element_by_css_selector('h1')
                line['Name'] = name.text.encode('ascii', 'ignore').decode('utf-8')

                line['Source'] = link
                

                values = bus.driver.find_elements_by_class_name('company-info-value')
##                print('Blocks: ', values)
                i=0
                for value in values:
    ##                    print('Value: ', value.text)
    ##                    print('Creating value list')
                    valueData.append(value.text.encode('ascii', 'ignore').decode('utf-8'))
    ##                    print('Value line: ',valueLine)
    ##                    print('Value data: ', valueData)
                    i = i+1

                titles = bus.driver.find_elements_by_class_name('company-info-title')
##                print('Blocks: ', titles)
                i=0
                for title in titles:
    ##                    print('Title: ', title.text)
    ##                    print('Value line ', i, ': ',valueData[i])
    ##                print('Creating title list')

                    line[title.text] = valueData[i]       #this is a dictionary (because I'm stupid and can never remember which syntax is a list                  

                    if title.text == 'Founders':                        
                        founderURLvalue = 'None'
##                        print('Searching for linkedin')
                        try:
                            founderURLs = values[i].find_elements_by_css_selector('a')
                            founderURLvalue = ''
                            for founderURL in founderURLs:
                                if founderURLvalue != '':
                                    founderURLvalue = founderURLvalue + '; ' + founderURL.get_attribute("href")
                                else:
                                    founderURLvalue = founderURL.get_attribute("href")
##                                print(founderURLvalue)

                                line['Founder URL'] = founderURLvalue
                        except NoSuchElementException:
                            print('No founder links found')
##                            continue                        

                    if title.text == 'Press URL':                        
                        pressURLvalue = 'None'
                        print('<<<Searching for press>>>')
                        try:
                            pressURLs = values[i].find_elements_by_css_selector('a')
                            pressURLvalue = ''
                            for pressURL in pressURLs:
                                if pressURLvalue != '':
                                    pressURLvalue = pressURLvalue + '; ' + pressURL.get_attribute("href")
                                else:
                                    pressURLvalue = pressURL.get_attribute("href")
                                print(pressURLvalue)

                                line['Press URL'] = pressURLvalue
                        except NoSuchElementException:
                            print('No press links found')
##                            continue                                                

                    i = i+1

                data.append(line)
                click.echo("Obtained ..." + link)            
##                print('Data: ', data)

                writer.writerows(data)



@click.command()
@click.option('--browser', default='phantomjs', help='Browser to run with')
@click.argument('outfile')                        
def crawl(browser, outfile):

    URL = 'https://www.techireland.org/companies'
    
    fieldnames = ['Company name', 'Company description', 'Company URL']
    # then check we can write the output file
    # we don't want to complete process and show error about not
    # able to write outputs
    with open(outfile, 'w', newline='') as csvfile:
        # just write headers now
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
    
    # now open the browser

    with WebBus(browser) as bus:
        bus.driver.get(URL)
        print("Opening page")

        with open(outfile, 'a+', newline='') as csvfile:
            print('Starting writer')
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)


            isnext = True
            while isnext==True:
                addresses = []
                
                print(bus.driver.current_url)  
##                URL = bus.driver.current_url
                print("creating list")                                       
                companies = bus.driver.find_elements_by_class_name('company-tile')
##                bus.driver.get(URL)
    ##            print(companies)
                for company in companies:
    ##                print(company)
                    urlElement = company.find_element_by_class_name('no-decoration')
    ##                print(urlElement)
                    companyURL = urlElement.get_attribute("href")

                    nameElement = company.find_element_by_css_selector('h2.text-left')
    ##                print(nameElement)
                    companyName = nameElement.text.encode('ascii', 'ignore').decode('utf-8')
                    
                    descElement = company.find_element_by_css_selector('p.text-left')
    ##                print(descElement)
                    companyDesc = descElement.text.encode('ascii', 'ignore').decode('utf-8')
                    data = {'Company name': companyName, 'Company description': companyDesc, 'Company URL': companyURL}
                    print('Data: ', data)
                    addresses.append(data)

    ##            print("Addresses: ", addresses)

                writer.writerows(addresses)
##                addresses.clear
                try:
                    print('Finding next page')
                    next_page = bus.driver.find_element_by_link_text('Next ›')
                    print('Page found: Clicking')
                    next_page.click()
                    print('Clicked: Waiting')                    
                    time.sleep(random.uniform(1, 4))
                    WebDriverWait(bus.driver, 20).until(    
                        EC.presence_of_element_located((By.CSS_SELECTOR, '.image-container'))
                    )
                except NoSuchElementException:
                    print('No next page')
                    isnext = False
                    continue
##            click.echo("Obtained ..." + companyurl)

cli.add_command(crawl)
cli.add_command(crawlcompanies)

if __name__ == '__main__':
    cli()
