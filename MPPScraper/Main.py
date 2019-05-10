import json
import urllib.parse
import os
import sys

from Config import Config
from EnhancedExecutor import EnhancedExecutor

def curl_proxy_joiner(c, p):
    return f"{c} -x {p}"

def save_json(json_dict, json_path, indent=4):
    print(f">> Writing JSON file to: {json_path}")
    path_dir = os.path.dirname(json_path)
    if not os.path.exists(path_dir):
        os.makedirs(path_dir)
    with open(json_path, 'w') as out_file:
        out_file.write(json.dumps(json_dict, indent=indent))

def read_json(json_path):
    print(f">> Reading JSON file from: {json_path}")
    with open(json_path, 'r') as in_file:
        return json.load(in_file)

def distinct_key(json_list, id_key):
    distinct_map = {json_entry[id_key]: json_entry for json_entry in json_list if json_entry.get(id_key, None) != None}
    return list(distinct_map.values())

# >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>> [EXECUTED METHODS] >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>> #

def approximate_pages(keywords, page_buffer):
    print(f">> Running: approximate_pages with (keywords:{keywords}, page_buffer:{page_buffer})")
    approx_template = "curl 'https://chalice-search-api.cloud.seek.com.au/search?siteKey=AU-Main&sourcesystem=houston&where=All+Australia&page=<PAGE>&seekSelectAllPages=true&keywords=<KEYWORDS>&include=seodata&isDesktop=true' -H 'Accept: application/json, text/plain, */*'"
    approx_replace_dict = {
        "<KEYWORDS>": [urllib.parse.quote_plus(keywords)], 
        "<PAGE>": [1], }
    enhancedExecutor = EnhancedExecutor(approx_template, approx_replace_dict, proxy_joiner=curl_proxy_joiner)
    results = enhancedExecutor.run_commands_on_workers()
    result_json = json.loads(enhancedExecutor.decode_result(results[0]))
    approx_pages = result_json['totalCount'] // (len(result_json['data']) - page_buffer)
    return approx_pages

def search_jobs(keywords, page_buffer=5):
    search_cache = os.path.join(*(Config.data_path, keywords, f"search_jobs.json"))
    if os.path.exists(search_cache): return read_json(search_cache)
    pages = approximate_pages(keywords, page_buffer)
    print(f">> Running: search_jobs with (keywords:{keywords}, pages:{pages})")
    search_template = "curl 'https://chalice-search-api.cloud.seek.com.au/search?siteKey=AU-Main&sourcesystem=houston&where=All+Australia&page=<PAGE>&seekSelectAllPages=true&keywords=<KEYWORDS>&include=seodata&isDesktop=true' -H 'Accept: application/json, text/plain, */*'"
    search_replace_dict = {
        "<KEYWORDS>": [urllib.parse.quote_plus(keywords)],
        "<PAGE>": list(range(1, pages + 1)), }
    search_workers = 6
    enhancedExecutor = EnhancedExecutor(search_template, search_replace_dict, search_workers, curl_proxy_joiner)
    results = enhancedExecutor.run_commands_on_workers()
    decoded_results = [enhancedExecutor.decode_result(result) for result in results]
    data_results = [data for decoded_result in decoded_results for data in json.loads(decoded_result)['data']]
    unique_data_results = distinct_key(data_results, 'id')
    save_json(unique_data_results, search_cache)
    return unique_data_results

def view_posts(keywords, ids):
    posts_cache = os.path.join(*(Config.data_path, keywords, f"view_posts.json"))
    if os.path.exists(posts_cache): return read_json(posts_cache)
    posts_template = "curl 'https://chalice-experience.cloud.seek.com.au/job/<ID>?isDesktop=true' -H 'Accept: application/json, text/plain, */*'"
    posts_dict = {"<ID>": ids, }
    posts_workers = 20
    enhancedExecutor = EnhancedExecutor(posts_template, posts_dict, posts_workers, curl_proxy_joiner)
    results = enhancedExecutor.run_commands_on_workers()
    decoded_results = [enhancedExecutor.decode_result(result) for result in results]
    data_results = [json.loads(decoded_result) for decoded_result in decoded_results]
    unique_data_results = distinct_key(data_results, 'id')
    save_json(unique_data_results, posts_cache)
    return unique_data_results

def view_applications(keywords, ids):
    applications_cache = os.path.join(*(Config.data_path, keywords, f"view_applications.json"))
    if os.path.exists(applications_cache): return read_json(applications_cache)
    applications_template = "curl 'https://ca-jobapply-ex-api.cloud.seek.com.au/jobs/<ID>?isDesktop=true' -H 'Accept: application/json, text/plain, */*'"
    applications_dict = {"<ID>": ids, }
    applications_workers = 20
    enhancedExecutor = EnhancedExecutor(applications_template, applications_dict, applications_workers, curl_proxy_joiner)
    results = enhancedExecutor.run_commands_on_workers()
    decoded_results = [enhancedExecutor.decode_result(result) for result in results]
    data_results = [json.loads(decoded_result) for decoded_result in decoded_results]
    unique_data_results = distinct_key(data_results, 'id')
    save_json(unique_data_results, applications_cache)
    return unique_data_results

# <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<< [EXECUTED METHODS] <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<< #

""" TODO:
        - lint using: flake8 --max-line-length=1000
        - better logger (timestamp + thread + level + ...) info
"""

if __name__ == '__main__':
    print("Usage: Arg1=keywords, ...")
    keywords = sys.argv[1]

    jobs = search_jobs(keywords)
    posts = view_posts(keywords, [job['id'] for job in jobs])
    applications = view_applications(keywords, [job['id'] for job in jobs])

    print('>> You may now interact with the data gathered (jobs, posts, applications). Enter "exit()" to stop.')
    import code; code.interact(local={**locals(), **globals()})
