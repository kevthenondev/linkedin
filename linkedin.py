# -*- coding: utf-8 -*-
"""
Simple Linkedin crawler to collect user's  profile data.

@author: idwaker

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
from selenium.common.exceptions import (WebDriverException, NoSuchElementException)
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

import re
import random

LINKEDIN_URL = 'https://www.linkedin.com'
INITIAL_PAGE_NUMBER = 1
MAX_PAGE_NUMBER = 15

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
        names = [line[:-1] + ' in people' for line in _file.readlines()]
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
@click.argument('infile')
@click.argument('outfile')
def crawl(browser, username, infile, outfile):
    """
    Run this crawler with specified username
    """

    # first check and read the input file
    all_names = collect_names(infile)

    fieldnames = ['occupation','courses_list']
    # then check we can write the output file
    # we don't want to complete process and show error about not
    # able to write outputs
    with open(outfile, 'w', newline='') as csvfile:
        # just write headers now
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()

    link_title = './/a[@class="search-result__result-link"]'

    # now open the browser
    with WebBus(browser) as bus:
        bus.driver.get(LINKEDIN_URL)

        login_into_linkedin(bus.driver, username)

        for name in all_names:
            click.echo("Getting ...")
            print(name)
            try:
                search_input = bus.driver.find_element_by_css_selector('.ember-view input')
            except NoSuchElementException:
                print('NoSuchElementException search_input')
                continue
            search_input.send_keys(name)
            try:
                # search_form = bus.driver.find_element_by_class_name('nav-search')
                # print('search_form:',search_form)
                # search_form.submit()
                bus.driver.find_element_by_css_selector('.search-typeahead-v2__button').click()
            except NoSuchElementException:
                print('click search button failes')

            profiles = []

            # collect all the profile links
            results = None
            try:
                results = WebDriverWait(bus.driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, ".search-results__primary-cluster"))
                )
            finally:
                # run through pages
                print(bus.driver.current_url)

                url = bus.driver.current_url + "&page=1"
                for i in range(INITIAL_PAGE_NUMBER, MAX_PAGE_NUMBER):
                    page_url = re.sub(r"&page=\d+", "&page=" + str(i), url)
                    bus.driver.get(page_url)

                
                    try:
                        links = bus.driver.find_elements_by_css_selector(".search-result__info .search-result__result-link")
                    except NoSuchElementException:
                        print('links failed', NoSuchElementException)
                    links = [link.get_attribute('href') for link in links]
                    # print('links:',links)
                    with open(outfile, 'a+', newline='') as csvfile:
                        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                        for link in links:
                            # every search result
                            print('link:',link)
                            time.sleep(random.uniform(0.2, 7))

                            bus.driver.get(link)
                            # Might need to login in the middle
                            # try:
                            #     login_into_linkedin(bus.driver, username)
                            #     print('login again')
                            #     bus.driver.get(link)
                            # except:
                            #     pass

                            accomplishments = None

                            # scorll down to get accomplishment
                            # Get scroll height
                            last_height = bus.driver.execute_script("return document.body.scrollHeight")

                            while True:
                                # Scroll down to bottom
                                bus.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")

                                # Wait to load page
                                time.sleep(random.uniform(0.2, 7))

                                # Calculate new scroll height and compare with last scroll height
                                new_height = bus.driver.execute_script("return document.body.scrollHeight")
                                if new_height == last_height:
                                    break
                                last_height = new_height

                            try:
                                # results = WebDriverWait(bus.driver, 10).until(
                                #     EC.presence_of_element_located((By.CSS_SELECTOR, ".pv-accomplishments-block__content"))
                                # )
                                accomplishments = bus.driver.find_elements_by_class_name('pv-accomplishments-block__content')
                            except NoSuchElementException:
                                click.echo("No accomplishments section skipping this user")
                                continue
                            print('accomplishments:',accomplishments)
                            for accomplishment in accomplishments:
                                title = accomplishment.find_element_by_class_name('pv-accomplishments-block__title');
                                print('text:',title.text)
                                if  title.text != 'Courses':
                                    continue
                                
                                print('Courses')
                                try:
                                    accomplishment.find_element_by_class_name('.svg-icon-wrap').click()
                                    print(accomplishment.find_element_by_class_name('pv-profile-section__see-more-inline'))
                                    while (accomplishment.find_element_by_class_name('pv-profile-section__see-more-inline')):
                                        accomplishment.find_element_by_class_name('pv-profile-section__see-more-inline').click();
                                    courses = accomplishment.find_elements_by_class_name('pv-accomplishments-block__list li')

                                except NoSuchElementException:
                                    print('no svg-icon-wrap')
                                    courses = accomplishment.find_elements_by_css_selector('.pv-accomplishments-block__summary-list li')
                                    

                                if courses:
                                    courses_list = []
                                    # collect all course names
                                    for course in courses:
                                        courses_list.append(course.text)
                                    data = {
                                        'occupation': bus.driver.find_element_by_class_name('pv-top-card-section__headline').text,
                                        'courses_list': courses_list,
                                    }
                                    print(data)
                                    profiles.append(data)
                                    writer.writerows(profiles)
                                else:
                                    print('no class!')

                        click.echo("Obtained ..." + name)

@click.command()
@click.option('--browser', default='phantomjs', help='Browser to run with')
@click.argument('username')
@click.argument('infile')
@click.argument('outfile')                        
def crawlexperience(browser, username, infile, outfile):
    """
    Run this crawler with specified username
    """

    # first check and read the input file
    links = collect_urls(infile)   #get urls from file - could make a single smarter file reader proc

    fieldnames = ['url', 'name', 'title','company', 'dateRange', 'location']
    # then check we can write the output file
    # we don't want to complete process and show error about not
    # able to write outputs
    with open(outfile, 'w', newline='') as csvfile:
        # just write headers now
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
    
    link_title = './/a[@class="search-result__result-link"]'

    # now open the browser

    with WebBus(browser) as bus:
        bus.driver.get(LINKEDIN_URL)

        login_into_linkedin(bus.driver, username)
        # print('Logged in')
        # print('Survived sleep')
        with open(outfile, 'a+', newline='') as csvfile:
            # print('Starting writer')
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            time.sleep(random.uniform(10, 10))   #setup break to manually login
 
            for link in links:
                profiles = []
                # every search result
                print('link:',link)
                
                bus.driver.get(link)
                # login_in_the_middle(bus.driver, username)
                experienceBlock = None
                experiences = None
                                
                # scroll down to open experience
                last_height = bus.driver.execute_script("return document.body.scrollHeight")
                # print('Scrolling to bottom')
                while True:
                    bus.driver.execute_script("window.scrollBy(0, +300);")
                    # Wait to load page
                    time.sleep(random.uniform(1, 2))
                    bus.driver.execute_script("window.scrollBy(0, +300);")
                    # Wait to load page
                    time.sleep(random.uniform(1, 2))
                    bus.driver.execute_script("window.scrollBy(0, +300);")

                    # Calculate new scroll height and compare with last scroll height
                    new_height = bus.driver.execute_script("return document.body.scrollHeight")
                    if new_height == last_height:
                        break
                    last_height = new_height

                #limit to experience block so we don't mess with education dropdowns
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
                        click.echo("No date range data")
                        dateData = 'None'
                        # continue                        
                    try:
                        location = experience.find_element_by_class_name('pv-entity__location');
                        locationData = location.text.splitlines()[1]
                    except NoSuchElementException:
                        click.echo("No location data")
                        locationData = 'None'
                        # continue
                        # print('Allocated title data')
                    # print('Title text: ',title)
                    # print('Title text: ',title.text)

                    # print('Creating data entry')
                    data = {'url': link.encode('ascii', 'ignore').decode('utf-8'),
                                'name': name.text.encode('ascii', 'ignore').decode('utf-8'),
                                'title': title.text.encode('ascii', 'ignore').decode('utf-8'),
                                'company': company.text.encode('ascii', 'ignore').decode('utf-8'),
                                'dateRange': dateData.encode('ascii', 'ignore').decode('utf-8'),
                                'location': locationData.encode('ascii', 'ignore').decode('utf-8')}
                    # print('Data: ',data)
                    profiles.append(data)
                    # print(profiles)
                writer.writerows(profiles)
                click.echo("Obtained ..." + link)

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
cli.add_command(store)


if __name__ == '__main__':
    cli()
