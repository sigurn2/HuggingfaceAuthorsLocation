from __future__ import annotations

import csv
import os
from typing import Any


def retry(max_retries=3, wait_time=1):
    import time
    def decorator(func):
        def wrapper(*args, **kwargs):
            retries = 0
            while retries < max_retries:
                try:
                    return func(*args, **kwargs)
                except:
                    retries += 1
                    print(f'Retry {retries}/{max_retries} after {wait_time} second(s) ...')
                    time.sleep(wait_time)
            print(f'Failed after {max_retries} retries')

        return wrapper

    return decorator


def getPageList(source: str) -> list:
    import requests

    target_item = 1000  # 所需数据总量
    link_collection = []
    base_url = 'https://huggingface.co'
    n = 0
    while n < target_item / 30:
        site = base_url + '/' + source + '?p=' + str(n) + '&sort=likes'  # 组装请求地址， 按照 like 数排序
        print(site, n)
        response = requests.get(site)
        response.encoding = 'utf-8'
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(response.text, 'lxml')
        hugging_faces = soup.select('article')  # 爬取 article 列表
        for huggingface in hugging_faces:
            if len(link_collection) >= target_item:
                return link_collection
            a = huggingface.find('a')
            t = a['href']
            link_collection.append(base_url + t)  # 选择每个元素的 url
        n += 1
    return link_collection


@retry(max_retries=3, wait_time=1)
def getAuthor(url: str) -> list[Any] | None:
    import requests
    import re

    author_list = []

    # 发送HTTP请求并获取网页内容
    try:
        response = requests.get(url)

        html_content = response.text

        # 使用正则表达式提取author={}括号中的内容
        pattern = r'author=\{(.*?)\}'
        matches = re.findall(pattern, html_content)
        if len(matches) == 0:
            return None
        for match in matches:  # 可能会有多条 citation
            for name in match.split('and'):  # 从每条 citation 中的@author 中提取具体 author
                name = name.replace(",", " ")
                author_list.append(name)
        return author_list
    except requests.exceptions.RequestException:
        return None


def github_worm(author_list: list):
    from github import Github
    from github import Auth

    area_list = []

    token = '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'
    auth = Auth.Token(token)

    g = Github(auth=auth)
    g.default_retry = 3
    # 获取API限制信息
    rate_limit = g.get_rate_limit()

    # 获取核心限制（Core limit）
    core_limit = rate_limit.core

    # 打印核心限制信息
    print(f"剩余请求数量: {core_limit.remaining}")
    print(f"总请求数量: {core_limit.limit}")

    for author in author_list:
        query = 'language:python ' + author
        cnt = 0
        try:
            users = g.search_users(query, sort='followers', order='desc')
            for user in users:
                if user.location is not None:
                    area_list.append(user.location)
                break
        except urllib3.exceptions.MaxRetryError:
            cnt += 1
            print(f"{cnt} of {len(author_list)} failed")

    g.close()
    return area_list


def save(path: str, obj: list):
    with open(path, "a", newline="") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(obj)


if __name__ == '__main__':
    from tqdm import tqdm

    model = 'models'
    dataset = 'datasets'
    model_path = 'model.csv'
    dataset_path = 'data.csv'
    if not os.path.exists(model_path) and not os.path.exists(dataset_path):
        model_list = getPageList(model)
        save(model_path, model_list)
        dataset_list = getPageList(dataset)
        save(dataset_path, dataset_list)

    author_list = 'author.csv'
    if not os.path.exists('success.csv'):
        with open(model_path, "r") as csvfile:
            reader = csv.reader(csvfile)

        for row in reader:
            url_list = row
            for url in tqdm(url_list, desc='Progress', unit='URL'):
                if getAuthor(url) is not None:
                    save(author_list, getAuthor(url))

    author_map = {}
    with open('author.csv', 'r') as author:
        reader = csv.reader(author)
        for row in reader:
            for name in row:
                t = name.lower().strip()
                if t not in author_map:
                    author_map[t] = 1
                else:
                    author_map[t] += 1
    print(len(author_map))

    from github import Github
    from github import Auth

    token = 'YOUR_GITHUB_TOKEN'
    auth = Auth.Token(token)

    g = Github(auth=auth)

    wait_list = {}
    location_dict = {}
    cnt = 1
    for name, mul in author_map.items():

        query = 'language:python ' + name
        try:
            users = g.search_users(query, sort='followers', order='desc')
            # 计算需要延迟的时间（60秒 / 5000次 = 0.012秒/次）
            delay = 0.024
            # # 暂停执行
            # time.sleep(delay)
            for user in users:
                if user.location is not None:
                    if user.location not in location_dict:
                        location_dict[user.location] = mul

                        break
                    else:
                        location_dict[user.location] += mul
            print(f"{cnt} of {len(author_map)} fin")
            cnt += 1

        except Exception as e:
            if name not in wait_list:
                wait_list[name] = mul
            print(f"wait list append {name} ")

    if len(wait_list) == 0:
        g.close()
    else:
        while len(wait_list) != 0:
            wait_list = {}
            for name, mul in wait_list.items():

                query = 'language:python ' + name
                try:
                    users = g.search_users(query, sort='followers', order='desc')
                    # 计算需要延迟的时间（60秒 / 5000次 = 0.012秒/次）
                    delay = 0.024
                    # # 暂停执行
                    # time.sleep(delay)
                    for user in users:
                        if user.location is not None:
                            if user.location not in location_dict:
                                location_dict[user.location] = mul
                                break
                            else:
                                location_dict[user.location] += mul
                    print(f"{cnt} of {len(author_map)} fin")
                    cnt += 1

                except Exception as e:
                    if name not in wait_list:
                        wait_list[name] = mul
                    print(f"wait list append {name} ")

    loc_path = 'loc_model.csv'
    fieldnames = list(location_dict.keys())
    with open(loc_path, 'w', newline='') as loc:
        writer = csv.DictWriter(loc, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerow(location_dict)

    wl_path = 'waitlist_model.csv'
    p = list(wait_list.keys())
    with open(wl_path, 'w', newline='') as loc:
        writer = csv.DictWriter(loc, fieldnames=p)
        writer.writeheader()
        writer.writerow(wait_list)


    def read_csv_as_dict(file_path):
        data = {}
        with open(file_path, 'r', newline='') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                # 假设 CSV 文件中的第一列作为键，其余列作为值
                key = row.pop(reader.fieldnames[0])
                data[key] = row
        return data


    author_map = read_csv_as_dict('waitlist_model.csv')
    print("success")