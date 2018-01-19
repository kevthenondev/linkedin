Linkedin Web Search and Experience Crawler
==========================================

WIP
---


To install (Python 3)

::

    $ python -m venv venv
    $ ./venv/bin/pip install -r requirements.txt
    
Ubuntu

::

    $ sudo apt-get update && sudo apt-get upgrade
    $ sudo apt-get install build-essentials python-dev libssl-dev libffi-dev
    $ sudo apt-get install python-virtualenv
    $ virtualenv venv
    $ ./venv/bin/pip install pip --upgrade
    $ ./venv/bin/pip install -r requirements.txt
    $ ./venv/bin/pip install pyopenssl [ incase of insecure warning / or just to be safe ]

To store password in keychain

::

    $ python linkedin.py store me@email.com
    Password: **


To run crawler

::

    $ python linkedin.py crawl me@email.com list_of_names.csv dump_profiles_here.csv --browser=firefox
(this comes from previous fork)
OR

::

    $ python linkedin.py crawlexperience me@email.com list_of_urls.csv list_of_random_urls.csv dump_profiles_here.csv --browser=firefox
(this was added after the fork)

======

Environment 2017

Download geckodriver and chromedriver (if you're using Chrome, otherwise, firefoxdriver)
export PATH=$PATH:/path/to/your/driver
Should have selenium installed

To get this to work on python2, you'll need to fix the encoding when writing to the csv. Everything else seems to work.
