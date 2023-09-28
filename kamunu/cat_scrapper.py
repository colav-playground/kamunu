from urllib.parse import unquote
from bs4 import BeautifulSoup
from fuzzywuzzy import fuzz
import requests


def url_finder(data: str, verbose=0) -> list:

    global webpages
    webpages = ['edurank.org', 'crunchbase.com', 'unipage.net', '4icu.org']

    query = data.replace(' ', '+').lower()

    valids = []

    def duckduckgo(query: str, web: str, verbose) -> list:
        rs = []
        furl = f"https://duckduckgo.com/html/?q={query}"
        if verbose != 0:
            print(f'searching {furl} with DuckDuckGo')
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3"}

        try:
            response = requests.get(furl, headers=headers)
        except requests.exceptions.RequestException as e:
            raise Exception(f'DuckDuckGo: An error occurred (duckduckgo): {e}')

        if response:
            soup = BeautifulSoup(response.text, 'html.parser')
            completeData = soup.find_all("a", {"class": "result__a"})
            if completeData:
                for i, result in enumerate(completeData):
                    href = result['href']
                    if 'wiki' in href:
                        continue
                    rs.append(href)
                    break

            else:
                if verbose != 0:
                    print("Warning!, not DuckDuckGo scrapping")
                return None

        if rs:
            return rs

        return None

    def google(query: str, web: str, verbose) -> list:
        rs = []
        webb = 'www.' + web
        furl = f'https://www.google.com/search?q={query}'
        if verbose != 0:
            print(f'searching {furl} with Google')

        try:
            session = requests.Session()
            response = session.get(furl)
        except requests.exceptions.RequestException as e:
            raise Exception(f'Google: An error occurred (google): {e}')

        if response:
            soup = BeautifulSoup(response.text, 'html.parser')
            completeData = soup.find_all('a', href=True)

            if completeData:
                for i, result in enumerate(completeData):
                    href = result['href']
                    if webb in href:
                        url = href.split('=')[1].split("&")[0]
                        if 'wiki' in url:
                            continue
                        rs.append(unquote(url))
                        break

                    elif web == 'edurank.org':
                        webb = 'https://' + web
                        if webb in href:
                            rs.append(unquote(url))
                            break

            else:
                if verbose != 0:
                    print("Warning!, not DuckDuckGo scrapping")
                return None

        if rs:
            return rs

        return None

    # Script start
    for web in webpages:
        fquery = query + "+" + web
        if verbose != 0:
            print(f'Query: "{fquery}" for {web}')

        urls = duckduckgo(fquery, web, verbose)
        if urls:
            for url in urls:
                valids.append(url)
            if verbose != 0:
                print(f'URLs found with DuckDuckGo for {web}\n{valids}\n')

        else:
            if verbose != 0:
                print('\nSwitching to Google search')
            urls = google(fquery, web, verbose)
            if urls:
                for url in urls:
                    valids.append(url)
                if verbose != 0:
                    print(f'URLs found with Google for {web}\n{valids}\n')

    if valids:
        return valids

    return None


def cat_scrapper(data: str, urls: list) -> list:
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3"}
    types_words = ['nonprofit', 'forprofit', 'private',
                   'public', 'mixed', 'hybrid', 'non-profit', 'for-profit']
    types = set()
    sources = set()

    filtered_urls = []

    for url in urls:
        if '.4icu.org' in url:
            filtered_urls.append(url)

        for part in url.split('/'):
            if part:
                fpart = part.replace('-', ' ').replace('_', ' ')
                fuzzy = fuzz.token_set_ratio(data.lower(), unquote(fpart))
                # print(fuzzy, data.lower(), unquote(fpart))
                if fuzzy >= 60:
                    filtered_urls.append(url)

    for url in filtered_urls:
        if 'crunchbase.com' in url:
            r = requests.get(url, headers=headers)
            soup = BeautifulSoup(r.text, 'html.parser')
            elements = soup.find_all(
                class_="component--field-formatter field-type-enum ng-star-inserted")
            for element in elements:
                word = element.get('title').lower()
                for ttype in types_words:
                    fu = fuzz.token_set_ratio(word, ttype)
                    if fu == 100:
                        types.add(ttype)
                        sources.add(url)

        if 'edurank.org' in url:
            try:
                edulink = f"{url.split('/')[0]}//{url.split('/')[2]}/{url.split('/')[3]}/{url.split('/')[4]}/"
            except Exception:
                edulink = url

            edurank = requests.get(
                url, headers=headers).text if 'rankings/' not in url else requests.get(edulink, headers=headers).text
            soup = BeautifulSoup(edurank, 'lxml')
            if soup:
                for dd_ in soup.find_all('dd', class_="dl-data__data mw-100 text-truncate"):
                    for word in types_words:
                        if word in dd_.text.lower():
                            types.add(word)
                            sources.add(edulink)

        if '4icu.org' in url:
            _4icu = requests.get(url, headers=headers).text
            if _4icu:
                soup = BeautifulSoup(_4icu, 'lxml')

            if soup:
                for stg in soup.find_all('strong'):
                    for word in types_words:
                        if word in stg.text.lower():
                            types.add(word)
                            sources.add(url)

            else:
                text_prof = soup.find_all(
                    'p', class_="text-justify")[0].text.lower()
                for word in types_words:
                    if word in text_prof:
                        types.add(word)
                        sources.add(url)

        if 'unipage.net' in url:
            unipage = requests.get(url, headers=headers).text
            soup = BeautifulSoup(unipage, 'lxml')
            if soup:
                for item in soup.find_all(class_="context context_primary context_first context_padding context_cta-bottom"):
                    for text in item.find_all('p'):
                        for word in types_words:
                            if word in text.get_text().lower():
                                types.add(word)
                                sources.add(url)

    types_list = list(types)
    sources_list = list(sources)

    return types_list, sources_list


def categories(data: str):
    urls = url_finder(data)
    if urls:
        types, sources = cat_scrapper(data, urls)
        if types:
            result = {
                'wikidata': None,
                'ror': None,
                'web': {
                    'values': types,
                    'sources': sources
                },
                'colav': []
            }

        return result

    return None, None
