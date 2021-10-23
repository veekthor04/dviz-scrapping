# dviz-scraping
A web scraping script using selenium

## Table of Contents
- [Requirements](#Requirements)
- [Usage](#Usage)

##  Requirements
- python
- a chrome driver (alternative was to use webdriver-manager)

## Usage
- install requirements
 
`$ pip install -r requirements.txt`

- create a .env file using the .env.sample file as a template

- enter python cli

`>>> from scrap_it import CredSurfer`

`>>> surf = CredSurfer()`

- get filter results in a .xlsx file and a list

`>>> surf.filter_by_location(radius='100 mi.', zip=94105, limit=10)`

### Alternative usage
- run script

`$ python scrap_it`
