# -*- coding: utf-8 -*-
"""
Simple Linkedin crawler to interate through a list of urls, pausing to allow a break so that I can browse the page to ensure it the correct one. The file copies the experience as proof that the person is the correct one (as the current job may not be the identifying company). It also has a method to find unlinked founders so I can pass the link back to techireland so that they can link to the linkedin profiles on their website. Finally, a basic google search is iterated to do a quick desktop search for missing founders. Basically, all this does is saves me from using copy-paste into the url so often. Limited automation of pasting links into the browser so I can focus on reading the pages.
.

To use this you need linkedin account, all search is done through your account

Requirements:
    python-selenium
    python-click
    python-keyring

Tested on Python 3 not sure how Python 2 behaves
"""

import sys
import csv
import time
import click
import getpass
import keyring
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import (WebDriverException, NoSuchElementException)
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

import re
import random

LINKEDIN_URL = 'https://www.linkedin.com'
INITIAL_PAGE_NUMBER = 1
MAX_PAGE_NUMBER = 1  # I turned this off - if I can't find the right person in 1 page, they're too difficult to find

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


def get_password(username):
    """
    get password from stored keychain service
    """
    password = keyring.get_password('linkedinpy', username)
    if not password:
        raise UnknownUserException("""You need to store password for this user
                                        first.""")

    return password


def login_into_linkedin(driver, username):
    """
    Just login to linkedin if it is not already loggedin
    """
    # print('starting login')
    userfield = driver.find_element_by_id('login-email')
    passfield = driver.find_element_by_id('login-password')

    submit_form = driver.find_element_by_class_name('login-form')

    password = get_password(username)

    # If we have login page we get these fields
    # I know it's a hack but it works
    # print('starting login entry')

    if userfield and passfield:
        userfield.send_keys(username)
        passfield.send_keys(password)
        submit_form.submit()
        click.echo("Logging in")

def login_in_the_middle(driver, username):

    userfield = driver.find_element_by_css_selector('.form-email input')
    passfield = driver.find_element_by_class_name('password')

    submit_form = driver.find_element_by_id('login')

    password = get_password(username)

    # If we have login page we get these fields
    # I know it's a hack but it works
    if userfield and passfield:
        userfield.send_keys(username)
        passfield.send_keys(password)
        submit_form.submit()
        click.echo("Logging in")

def collect_names(filepath):
    """
    collect names from the file given
    """
    names = []
    with open(filepath, 'r') as _file:
        # names = [line.strip() for line in _file.readlines()]
        names = [line[:-1] for line in _file.readlines()]
    return names

        
def collect_urls(filepath):
    """
    collect urls from the file given
    """
    items = []
    with open(filepath, 'r') as _file:
        # names = [line.strip() for line in _file.readlines()]
        items = [line[:-1] + '' for line in _file.readlines()]
    return items


@click.group()
def cli():
    """
    First store password

    $ python linkedin store username@example.com
    Password: **

    Then crawl linkedin for users

    $ python linkedin crawl username@example.com with_names output.csv --browser=firefox
    """
    pass


@click.command()
@click.option('--browser', default='phantomjs', help='Browser to run with')
@click.argument('username')
@click.argument('infile')   #this file has the name and company in a string - should only be one or two possibilities that are the correct profile that techireland needs to display
@click.argument('outfile')
def crawl(browser, username, infile, outfile):
    """
    Run this crawler with specified username
    """

    # first check and read the input file
    all_names = collect_names(infile)

    fieldnames = ['Search name', 'Name', 'URL']
    # then check we can write the output file
    # we don't want to complete process and show error about not
    # able to write outputs
    with open(outfile, 'w', newline='') as csvfile:
        # just write headers now
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()


    # now open the browser
    with WebBus(browser) as bus:

        bus.driver.get(LINKEDIN_URL)

        login_into_linkedin(bus.driver, username)
        time.sleep(random.uniform(30, 60))

        for name in all_names:
            links = []
            nametexts = []
            try:
                search_input = bus.driver.find_element_by_css_selector('.ember-view input')
                print('Found search box')
                time.sleep(random.uniform(2, 5))
            except NoSuchElementException:
                print('NoSuchElementException search_input')
                continue
            search_input.clear()
            search_input.send_keys(name)
            print('Input name: ', name)
            time.sleep(random.uniform(2, 5))
            try:
                bus.driver.find_element_by_css_selector('.search-typeahead-v2__button').click()
                print('Clicked search')
                time.sleep(random.uniform(5, 10))
            except NoSuchElementException:
                print('Click search button fails')

            profiles = []

            # collect the profile links - later I'll iterate through the experience to decide which is the right one
            results = None
            print('Current URL: ', bus.driver.current_url)
            
            try:
                links = bus.driver.find_elements_by_css_selector(".search-result__info .search-result__result-link")
            except NoSuchElementException:
                print('Links failed', NoSuchElementException)

            links = [link.get_attribute('href') for link in links]
            print('Links:', links)
            if links != []:
                i = 0
                try:
                    nametexts = bus.driver.find_elements_by_css_selector("span.name.actor-name")
                    nametexts = [nametext.text for nametext in nametexts]
                except NoSuchElementException:

                    print('Name texts failed', NoSuchElementException)
                while len(links)>len(nametexts):
                    nametexts.append("No name found")
                    print('Appended name')
                    
                print('Name texts:', nametexts[i])
                with open(outfile, 'a+', newline='') as csvfile:
                    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                    for link in links:
                        # every search result
                        print('Link: ', link)
                        print('Name text: ', nametexts[i])
##                        time.sleep(random.uniform(0.2, 2))

                        data = {'Search name': name.encode('ascii', 'ignore').decode('utf-8'), 'Name': nametexts[i].encode('ascii', 'ignore').decode('utf-8'), 'URL': link}
                        print(data)
                        profiles.append(data)
                        i = i + 1
                    writer.writerows(profiles)
                click.echo("Checked: " + name)
            else:
                print("Not found: " + name)
            time.sleep(random.uniform(2, 5))

@click.command()
@click.option('--browser', default='phantomjs', help='Browser to run with')
@click.argument('username')
@click.argument('infile')
@click.argument('inrandomfile')
@click.argument('outfile')                        
def crawlexperience(browser, username, infile, inrandomfile, outfile):
    """
    Run this crawler with specified username
    """

    # first check and read the input file
    links = collect_urls(infile)   #get urls from file - could make a single smarter file reader proc
##    randomsites = collect_urls(inrandomfile)   #get urls from file - used to make sure I'm not getting mixed up between profiles

    fieldnames = ['Number', 'Link', 'Resolved URL', 'Name', 'Title','Company', 'Date Range', 'Location']
    # then check we can write the output file
    # we don't want to complete process and show error about not
    # able to write outputs
    with open(outfile, 'w', newline='') as csvfile:
        # just write headers now
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
    
    # now open the browser

    with WebBus(browser) as bus:
##        driver = webdriver.Firefox()
##        driver = webdriver.Remote(command_executor="http://127.0.0.1:59456",desired_capabilities={})
##        driver.session_id = '6efbea68-f5ec-4b7f-8470-0c966e96f545'
     
        print(bus.driver.command_executor._url)
        print(bus.driver.session_id)

##        bus.driver = driver

        bus.driver.get(LINKEDIN_URL)
        
        login_into_linkedin(bus.driver, username)
        print('Logged in')
        time.sleep(random.uniform(60, 60))   #setup break to manually login
        # print('Survived sleep')
        with open(outfile, 'a+', newline='') as csvfile:
            # print('Starting writer')
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            time.sleep(random.uniform(5, 15))   #setup break to manually login
            i=0
            for link in links:
                i=i+1
##                randomsite = randomsites[int(random.uniform(0, 500))]
##                print('Random site: ', str(randomsite))
##                bus.driver.get(str(randomsite))
                time.sleep(random.uniform(30, 60))   #setup break to manually browse current page including login page
                profiles = []
                # every search result
                print('Link ', str(i) + ': '+ link)
                
                bus.driver.get(link)
                # login_in_the_middle(bus.driver, username)
                experienceBlock = None
                experiences = None

                try:
                    bus.driver.find_element_by_class_name('profile-unavailable')
                    print('Profile is unavailable')
##                    randomsite = randomsites[int(random.uniform(0, 500))]
##                    print('Random site: ', str(randomsite))
##                    bus.driver.get(str(randomsite))
                    time.sleep(random.uniform(15, 30))   #setup break to manually login
                    bus.driver.get(link)
                except NoSuchElementException:
                    print('Profile found')
                
                # scroll down to open experience so I can look for the techireland company
                last_height = bus.driver.execute_script("return document.body.scrollHeight")
                time.sleep(random.uniform(30, 60))   #setup break to manually login
                # print('Scrolling to bottom')
                while True:
                    bus.driver.execute_script("window.scrollBy(0, +"+str(int(random.uniform(1000,1500)))+");")
                    # Wait to load page
                    time.sleep(random.uniform(1, 2))
                    bus.driver.execute_script("window.scrollBy(0, -"+str(int(random.uniform(1000,1500)))+");")
                    # Wait to load page
                    time.sleep(random.uniform(1, 2))
                    bus.driver.execute_script("window.scrollBy(0, +"+str(int(random.uniform(200,400)))+");")
                    # Wait to load page
                    time.sleep(random.uniform(1, 2))
                    bus.driver.execute_script("window.scrollBy(0, +"+str(int(random.uniform(200,400)))+");")
                    # Wait to load page
                    time.sleep(random.uniform(1, 2))
                    bus.driver.execute_script("window.scrollBy(0, +"+str(int(random.uniform(200,400)))+");")

                    # Calculate new scroll height and compare with last scroll height
                    new_height = bus.driver.execute_script("return document.body.scrollHeight")
                    if new_height == last_height:
                        break
                    last_height = new_height

                #get the experience block as proof - too complicated to get just the right company as it's name may vary slightly (e.g. include Limited, Ltd. Group etc)
                try:                                        
                    experienceBlock = bus.driver.find_element_by_class_name('experience-section')
                    # print('Experience Block: ', experienceBlock)
                except NoSuchElementException:
                    click.echo("No experience section skipping this user")
                    continue

                name = bus.driver.find_element_by_class_name('pv-top-card-section__name')
                # print('Name: ', name.text)                
                    
                #scroll back to inline expansion and click on it                    
                while True:   
                    try:    
                        element = experienceBlock.find_element_by_class_name('pv-profile-section__see-more-inline')
                        # print('Found an inline expansion: scrolling back to click on it')
                        bus.driver.execute_script("return arguments[0].scrollIntoView();", element)
                        # print('Scrolled to element')
                        bus.driver.execute_script("window.scrollBy(0, -150);")
                        # print('About to click')
                        bus.driver.find_element_by_class_name('pv-profile-section__toggle-detail-icon').click()
                        # Wait to load page
                        time.sleep(random.uniform(1, 2))
                    except NoSuchElementException:
                        click.echo("No expand element found")
                        # continue                    
                    try:
                        moreInline = experienceBlock.find_element_by_class_name('pv-profile-section__see-more-inline')
                    except NoSuchElementException:
                        break


                experiences = experienceBlock.find_elements_by_class_name('pv-entity__summary-info')
                # print('Experiences:',experiences)
                        
                for experience in experiences:
                    # print('Parsing titles')

                    title = experience.find_element_by_tag_name('h3');
                    # print(title.text)
                    company = experience.find_element_by_class_name('pv-entity__secondary-title');
                    # print(company.text)
                    try:
                        dateRange = experience.find_element_by_class_name('pv-entity__date-range');
                        dateData = dateRange.text.splitlines()[1]
                    except NoSuchElementException:
##                        click.echo("No date range data")
                        dateData = 'None'
                        # continue                        
                    try:
                        location = experience.find_element_by_class_name('pv-entity__location');
                        locationData = location.text.splitlines()[1]
                    except NoSuchElementException:
##                        click.echo("No location data")
                        locationData = 'None'
                        # continue
                        # print('Allocated title data')
                    # print('Title text: ',title)
                    # print('Title text: ',title.text)

                    # print('Creating data entry')
                    data = {'Number': i, 'Link': link, 'Resolved URL': bus.driver.current_url,
                                'Name': name.text.encode('ascii', 'ignore').decode('utf-8'),
                                'Title': title.text.encode('ascii', 'ignore').decode('utf-8'),
                                'Company': company.text.encode('ascii', 'ignore').decode('utf-8'),
                                'Date Range': dateData.encode('ascii', 'ignore').decode('utf-8'),
                                'Location': locationData.encode('ascii', 'ignore').decode('utf-8')}
                    # print('Data: ',data)
                    profiles.append(data)
                    # print(profiles)
                writer.writerows(profiles)
                click.echo("Checked: " + link)

@click.command()
@click.option('--browser', default='phantomjs', help='Browser to run with')
@click.argument('infile')               
def crawlgoogle(browser, infile):
    """
    Run this crawler with specified username
    """

    # first check and read the input file
    searches = collect_urls(infile)   #get urls from file - could make a single smarter file reader proc

    # now open the browser
    with WebBus(browser) as bus:
     
        time.sleep(random.uniform(5, 15))   #setup break to manually login
        i=0
        for search in searches:
            i=i+1
            bus.driver.get("https://www.google.com");
            click.echo("Searching: " + str(i) + search)
            bus.driver.find_element_by_id("lst-ib").send_keys('"'+search+'"')
            time.sleep(random.uniform(3, 5))
            bus.driver.find_element_by_id("lst-ib").send_keys(Keys.RETURN)
            time.sleep(random.uniform(45, 45))   #setup break to manually login


@click.command()
@click.argument('username')
def store(username):
    """
    Store given password for this username to keystore
    """
    passwd = getpass.getpass()
    keyring.set_password('linkedinpy', username, passwd)
    click.echo("Password updated successfully")


cli.add_command(crawl)
cli.add_command(crawlexperience)
cli.add_command(crawlgoogle)
cli.add_command(store)


if __name__ == '__main__':
    cli()
