from random import randint 
import requests
from bs4 import BeautifulSoup
import csv
import time
import asyncio
import httpx
import re
import json
import pandas as pd

# HERE: Add the job titles you want to find
queries = ["CEO", "Digital Marketing Manager", "Product", "Whatever you want"]

# Enter your CSV file name
csv_file = "your_companies_name.csv"

# Enter the column name of companies name
companies_name_column = "companies_name_column"

results_file = "linkedin_results.json"
companies_name_file = "companies_name.json"


def extract_info(result):
    soup = BeautifulSoup(result, 'html.parser')
    try:
        title_element = soup.select_one('div > div > div > a > h3')
        link = soup.select_one('div.yuRUbf a')['href']
        link = check_urls(link)
        if link:
            title = title_element.get_text()
            if ' - ' in title:
                position = title.split(' - ')[1]
                name = title.split(' - ')[0]
            elif ' – ' in title:
                position = title.split(' – ')[1]
                name = title.split(' – ')[0]
            else:
                name = title
                if ' | ' in name:
                    name = name.split(' | ')[0]
                position = None
            return name, position, link
    except:
        pass
    return None, None, None


async def google_search(query):
    url = 'https://www.google.com/search?q=' + query
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
    async with httpx.AsyncClient() as client:
        response = await client.get(url, headers=headers)
        return response.text


def check_urls(link):
    pattern = r"https://(?:[a-z]{2}\.)?linkedin\.com/in/([a-zA-Z0-9-]+)/?(?:[?/][^/]+)?$"
    url = re.search(pattern, link).group(1)
    if (url):
        if '?' in link:
            link = link.split('?')[0]
        if '/en' in link:
            link = link.split('/en')[0]
        return link


def generate_linkedin_query(company, keywords):
    query = f'"{company}" site:linkedin.com '
    keyword_query = ' OR '.join(f'"{keyword}"' for keyword in keywords)
    query += f'({keyword_query})'
    print('query', query)
    return query


async def search_and_extract(company, queries):
    query = generate_linkedin_query(company, queries)
    results = await asyncio.gather(google_search(query))

    soup = BeautifulSoup(results[0], 'html.parser')
    extracted_info = []
    search_results = soup.select('div.g')
    for result in search_results:
        text = result.get_text()
        if 'Aimé par' not in text and 'Liked by' not in text:
            name, position, link = extract_info(str(result))
            if link:
                extracted_info.append(
                    {'Entreprise': company, 'Nom': name, 'Poste': position, 'Lien': link})
    return {'company': company, 'contacts': extracted_info}


def read_companies_from_file(filename):
    with open(filename, 'r') as json_file:
        data = json.load(json_file)
        if data.get('companies'):
            companies = data.get('companies', [])
    return companies


def write_companies():
    df = pd.read_csv(csv_file)
    company_names = df[companies_name_column].tolist()
    unique_company_names = list(set(company_names))
    data = {"companies": unique_company_names}
    with open(companies_name_file, 'w') as json_file:
        json.dump(data, json_file)


async def main():
    write_companies()
    companies = read_companies_from_file(companies_name_file)
    print(
        f"⚔️ Starting scrapping of {len(companies)} companies")
    results_json = []
    for company in companies:
        print(
            f"👉 Scrapping {company}")
        extracted_info = await search_and_extract(company, queries)
        results_json.append(extracted_info)
        time.sleep(randint(1, 4))

    with open(results_file, 'w', encoding='utf-8') as json_file:
        json.dump(results_json, json_file, ensure_ascii=False, indent=2)
    get_scraped_stats(results_file)


def get_scraped_stats(filename):
    with open(filename, 'r') as json_file:
        data = json.load(json_file)

    nb_companies = len(data)
    nb_contacts = sum(len(result["contacts"]) for result in data)
    print(
        f"🎯 Successfully found {nb_contacts} linkedins in {nb_companies} companies")


if __name__ == "__main__":
    asyncio.run(main())
