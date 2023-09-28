from concurrent.futures import ThreadPoolExecutor, as_completed
from deep_translator import GoogleTranslator as ts
from kamunu._version import get_version
from fuzzywuzzy import fuzz, process
from unidecode import unidecode
from bs4 import BeautifulSoup
from langdetect import detect
import translators as tss
import requests
import re

print(f'Kamunu {get_version()}')


def Kamunu(query):
    """
    Given a search query, the kamunu function performs searches on various search engines
    and retrieves information from the wikidata API. It then evaluates the results to provide
    the most relevant search results and returns them along with additional information.

    Args:
        query (str): The search query to be used for search operations.

    Returns:
        tuple: A tuple containing a dictionary of search results along with additional information
            and a dictionary of the original search results from different search engines.
    """

    # Helper function to check if the query contains non-ASCII characters and convert them if necessary.
    if not query.isascii():
        query = unidecode(query)

    # Pre-process the query by converting it to lowercase and removing parentheses.
    query = unidecode(query.lower().replace(')', '').replace('(', ''))
    term = query + ' wikidata ' + "site:wikidata.org"

    # Dictionary to store search results from different search engines.
    search_results = {'wikidata': ''}

    def wikiQsearch(id_: str) -> dict:
        """
        Given a Wikidata ID, this function fetches information about the entity from the Wikidata API.

        Args:
            id_ (str): Wikidata ID of the entity.

        Returns:
            dict: A dictionary containing information about the entity fetched from the Wikidata API.
        """
        try:
            r = requests.get(
                f'https://www.wikidata.org/wiki/Special:EntityData/{id_}.json').json()
            r = r['entities'][id_]
            return r
        except Exception as e:
            raise Exception(f'An error occurred (wikiQsearch): {e}')

    # Function to search for entities on Wikidata based on the query.
    def wikidata(query: str) -> dict:
        """
        This function searches for entities on Wikidata based on the given query.

        Args:
            query (str): The search query to be used for searching Wikidata.

        Returns:
            dict: A dictionary containing the search results from Wikidata.
        """
        sr = []
        wiki_hit = None
        base = 'https://www.wikidata.org/w/api.php'
        params = {"action": "wbsearchentities", "format": "json",
                  "search": query, "language": "en", "type": "item", "limit": 3}
        try:
            responses = requests.get(base, params=params, timeout=1).json()
            if responses['search']:
                wiki_hit_list = responses
            else:
                wiki_hit_list = None
        except Exception as e:
            raise Exception(f'wikidata: An error occurred (wikidata): {e}')

        if wiki_hit_list and 'search' in wiki_hit_list.keys():
            for wserch in wiki_hit_list['search']:
                match = unidecode(wserch['match']['text'])
                fz = fuzz.QRatio(query.lower(), match.lower())
                if fz and fz >= 95:
                    wiki_hit = wserch

        # Process the Wikidata search results and append relevant entity IDs to the 'sr' list.
        if wiki_hit:
            hit_label = wiki_hit['label'].lower()
            fl = fuzz.token_sort_ratio(query, hit_label)
            if 'aliases' in wiki_hit.keys():
                list_aliases = wiki_hit['aliases']
                fa = process.extract(query, list_aliases, limit=1)[0][1]
                if fl > 90 or fa > 90:
                    sr.append(wiki_hit['id'])
            elif fl > 90:
                sr.append(wiki_hit['id'])

        # Fetch detailed information about the first relevant entity from Wikidata.
        if sr:
            global q_
            q_ = wikiQsearch(sr[0])

        search_results = {'wikidata': sr}
        return search_results

    def wikipedia(query: str) -> dict:
        # Try searching on the Wikipedia API using the detected language.
        lang = detect(query)
        base = f'https://{lang}.wikipedia.org/w/api.php'
        params = {'action': 'query', 'format': 'json',
                  'list': 'search', 'srsearch': query}
        try:
            data = requests.get(base, params=params).json()
            if data["query"]["search"]:
                pageid = data["query"]["search"][0]["pageid"]
                params = {'action': 'query', 'format': 'json',
                          'pageids': pageid, 'prop': 'pageprops'}
                response = requests.get(base, params=params).json()
                wiki_id = response['query']['pages'][f'{pageid}']['pageprops']['wikibase_item']
                search_results = {'wikipedia': [wiki_id]}
                return search_results
            else:
                return None
        except Exception as e:
            raise Exception(
                f'wikidata: An error occurred (wikipedia): {e}')

    # Function to perform a Google search based on the given query and term.

    def google(query: str, term: str) -> dict:
        """
        This function performs a Google search using the given query and term.

        Args:
            query (str): The search query to be used for Google search.
            term (str): The search term to be used for Google search.

        Returns:
            dict: A dictionary containing the search results from Google.
        """
        sr = []
        term = term.replace(' ', '+')
        url = f'https://www.google.com/search?q={term}'

        try:
            session = requests.Session()
            response = session.get(url)
        except requests.exceptions.RequestException as e:
            raise Exception(f'Google: An error occurred (google): {e}')

        if response:
            soup = BeautifulSoup(response.text, 'lxml')
            completeData = soup.find_all("div", {"class": "yuRUbf"})

            if not completeData:
                completeData = soup.find(
                    'a', href=re.compile(r'wikidata.org/wiki/'))

                if completeData:
                    url = completeData['href']
                    qid = re.search(r'/wiki/(Q\d+)', url)
                    if qid:
                        sr.append(qid.group(1))
                else:
                    pass
                    # print("Warning! Not Google scraping")
            else:
                sr = [data.find("a").get("href").split('/')[-1]
                      for data in completeData if 'Q' in data.find("a").get("href")]

            return {'google': sr}

        return {'google': []}

    # Function to perform a DuckDuckGo search based on the given query and term.

    def duckduckgo(query: str, term: str) -> dict:
        """
        This function performs a DuckDuckGo search using the given query and term.

        Args:
            query (str): The search query to be used for DuckDuckGo search.
            term (str): The search term to be used for DuckDuckGo search.

        Returns:
            dict: A dictionary containing the search results from DuckDuckGo.
        """
        sr = []
        term = term.replace(' ', '+')
        url = f"https://duckduckgo.com/html/?q={term}"

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3"
        }

        try:
            response = requests.get(url, headers=headers)
        except requests.exceptions.RequestException as e:
            raise Exception(f'DuckDuckGo: An error occurred (duckduckgo): {e}')

        if response:
            soup = BeautifulSoup(response.text, 'html.parser')
            completeData = soup.find_all("a", {"class": "result__url"})

            if not completeData:
                print("Warning!, not DuckDuckGo scrapping")

            for i, result in enumerate(completeData):
                href = result['href']
                url = href.split('/')[-1]
                if url and 'Q' in url:
                    if url.split('Q')[-1].isdigit():
                        sr.append(url)
                        if i > 1:
                            break

            search_results = {'duckduckgo': sr}
            return search_results

        return {}

    def bing(query: str, term: str) -> dict:
        """
        This function performs a Bing search using the given query and term.

        Args:
            query (str): The search query to be used for Bing search.
            term (str): The search term to be used for Bing search.

        Returns:
            dict: A dictionary containing the search results from Bing.
        """
        sr = []
        term = term.replace(' ', '+')
        url = f'https://www.bing.com/search?q={term}'
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 6.3; WOW64; Trident/7.0; Touch; rv:11.0)"}
        try:
            response = requests.get(url, headers=headers)
        except requests.exceptions.RequestException as e:
            raise Exception(f'Bing: An error occurred (bing): {e}')

        if response:
            soup = BeautifulSoup(response.text, 'html5lib')
            completeData = soup.find_all("li", {"class": "b_algo"})
            if not completeData:
                print("Warning!, not Bing scrapping")

            for i in range(0, len(completeData)):
                url = completeData[i].find("a").get("href")
                wiki_id = url.split('/')[-1]
                if wiki_id and 'Q' in wiki_id:
                    if wiki_id.split('Q')[-1].isdigit():
                        sr.append(wiki_id)
                        if i > 1:
                            break

            search_results = {'bing': sr}
            return search_results
        return []

    # Function to find the most common ID from search results.
    def most_common_id(search_results: dict) -> list:
        """
        This function finds the most common ID from the search results.

        Args:
            search_results (dict): A dictionary containing the search results from different search engines.

        Returns:
            list: A list of most common IDs from the search results.
        """
        id_counter = {}

        for id_list in search_results.values():
            for idd in id_list:
                if idd in id_counter:
                    id_counter[idd] += 1
                else:
                    id_counter[idd] = 1

        if id_counter:
            not_repeted = all(value == 1 for value in id_counter.values())
            if not_repeted:
                return []

            most_c_id = max(id_counter, key=id_counter.get)

            if list(id_counter.values()).count(id_counter[most_c_id]) > 1:
                ids_repeated = []
                for ids, frec in id_counter.items():
                    if frec == id_counter[most_c_id]:
                        try:
                            org = wikiQsearch(ids)
                        except Exception as e:
                            print(
                                f'Error fetching organization data (most_common_id): {e}')
                            continue

                        lang = detect(query)
                        if org:
                            if lang in org['labels'].keys():
                                org_ = org['labels'][lang]['value']
                            elif 'en' in org['labels'].keys():
                                org_ = org['labels']['en']['value']
                            else:
                                for lang in org['labels'].keys():
                                    org_ = org['labels'][lang]['value']
                                    break

                            if fuzz.ratio(query, org_) >= 90:
                                ids_repeated = [ids]
                                break
                            else:
                                ids_repeated.append(ids)

                return ids_repeated

            else:
                return [most_c_id]

        return []

    # Function to perform verifications on the search results and return the verified IDs.
    def verifications(final_ids: list, query: str) -> list:
        """
        This function performs verifications on the search results and returns the verified IDs.

        Args:
            final_ids (list): A list of most common IDs from the search results.
            query (str): The search query used to perform the verifications.

        Returns:
            list: A list of verified IDs based on verifications.
        """
        response = []
        for Q in final_ids:
            try:
                q_ = wikiQsearch(Q)
            except Exception as e:
                print(f'Error fetching organization data (verifications): {e}')
                continue

            lang = detect(query)
            if lang != 'en':
                try:
                    tquery = ts(source='auto', target='en').translate(query)
                except Exception as e:
                    print(f'Error translating query (verifications): {e}')

                    langs = []
                    for word in query.split():
                        lang = detect(word)
                        langs.append(lang)

                    counts = {}
                    for element in set(langs):
                        counts[element] = langs.count(element)

                    lang = max(counts, key=counts.get)
                    tquery = tss.translate_text(
                        query, from_language=lang, to_language='en')
            else:
                tquery = query

            if q_:
                aliases = [inx['value'].lower() for key, values in q_[
                    'aliases'].items() for inx in values]
                qsplit = query.split()
                labels = [q_['labels'].get(lb).get(
                    'value').lower() for lb in q_['labels']]
                eOl = process.extractOne(query, labels)
                ll = eOl[1] >= 90 if eOl else 0
                teOl = process.extractOne(tquery, labels)
                lt = teOl[1] >= 95 if teOl else 0

                sitelinks = [q_['sitelinks'].get(lb).get(
                    'title') for lb in q_['sitelinks']]

                if sitelinks:
                    eOst = process.extractOne(query, sitelinks)
                    st = eOst[1] >= 95 if eOst else 0
                else:
                    st = False

                c = set(aliases) & set(qsplit)
                if c or ll or st or lt:
                    if 'P31' in q_['claims'].keys():
                        country = True if 'Q6256' in [
                            li['mainsnak']['datavalue']['value']['id'] for li in q_['claims']['P31']] else False
                        if not country:
                            response.append(Q)

        return response

    # Function to perform a search on the ROR (Research Organization Registry) database.
    def ror_search(response_wiki: list, query: str) -> str:
        """
        This function performs a search on the ROR (Research Organization Registry) database.

        Args:
            response_wiki (list): A list of verified IDs from Wikidata search results.
            query (str): The search query used to perform the ROR search.

        Returns:
            str: The ROR ID if found, otherwise an empty string.
        """
        if response_wiki:
            for Q in response_wiki:
                try:
                    q_ = wikiQsearch(Q)
                except Exception as e:
                    print(
                        f'Error fetching organization data (ror_search): {e}')
                    continue

                if 'claims' in q_.keys():
                    P = 'P6782'
                    ROR_ID = True if P in q_['claims'] else False
                    if ROR_ID:
                        ror_id = 'https://ror.org/' + \
                            q_['claims'][P][0]['mainsnak']['datavalue']['value']
                        return ror_id

        # If ROR ID not found, perform a search on the ROR API using the query.
        ror_url = 'https://api.ror.org/organizations?query='
        query_ = [query.replace(' ', '+').replace('  ', ' ').strip()]

        if '/' in query_[0]:
            query_ = query_[0].split('/')

        for qe_ in query_:
            rorsearch = ror_url + qe_
            try:
                ror = requests.get(rorsearch).json()
                if 'items' not in ror.keys():
                    return None
                ror_list = ror['items']

            except Exception as e:
                print(f'Error fetching ROR data (ror_search): {e}')
                return None

            ror_wikid = None

            for regss in ror_list:
                l_name = regss['name'].lower()
                for regs in regss.get('labels', []):
                    l_label = regs.get('label', '').lower()
                    ptr_n = fuzz.partial_token_sort_ratio(
                        qe_.replace('+', ' '), l_name)
                    ptr_l = fuzz.partial_token_sort_ratio(
                        qe_.replace('+', ' '), l_label)
                    if ptr_n > 95 or ptr_l > 95:
                        ror_id = regss['id']
                        if 'Wikidata' in regss['external_ids']:
                            ror_wikid = regss['external_ids']['Wikidata'].get(
                                'all')
                        return ror_id, ror_wikid

            return None

    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = []

        futures.append(executor.submit(wikidata, query))
        futures.append(executor.submit(wikipedia, query))
        futures.append(executor.submit(google, query, term))
        futures.append(executor.submit(duckduckgo, query, term))
        futures.append(executor.submit(bing, query, term))

        for future in as_completed(futures):
            try:
                search_results.update(future.result())

            except Exception as e:
                print('An error occurred (ThreadPoolExecutor): {}'.format(e))

    # If Wikidata search results are not available, perform verifications on the search results
    # and return the Wikidata link and ROR ID if found based on verifications.
    final_ids = most_common_id(search_results)

    if final_ids:
        response_wiki = verifications(final_ids, query)
        response_ror = ror_search(response_wiki, query)

        ror_wikid = None
        if response_ror and isinstance(response_ror, tuple):
            if response_ror[1]:
                ror_wikid = response_ror[1][0]

        if response_wiki:
            if response_wiki[0] and ror_wikid and response_wiki[0] != ror_wikid:
                response_ror = None

            response = {
                'wikidata': "https://www.wikidata.org/wiki/" + response_wiki[0],
                'ror': response_ror}
        else:
            response = {
                'wikidata': None,
                'ror': response_ror}
    else:
        reponse = None
        return reponse, search_results

    return response, search_results
