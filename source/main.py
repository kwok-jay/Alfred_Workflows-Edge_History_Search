import copy
import json
import sqlite3
import os
import sys
from urllib import parse

# 书签存在位置
booksDir = '/Users/kwok-jay/Library/Application Support/Microsoft Edge/Default/Bookmarks'
bookList = []

# 历史记录存在位置
historyDir = '/Users/kwok-jay/Library/Application\ Support/Microsoft\ Edge/Default/History'
# 指定一个历史记录缓存位置 避免database is locked
tempDir = './cache'
historyList = []


# 关键词查找逻辑
def AddList(allList, url, name, keylist):
    flag1 = 0
    flag2 = 0
    # 多个关键词同时在名称中包含 或者 多个关键词同时在url中包含
    for j in keylist:
        if j.lower() in name.lower():
            flag1 += 1
        # url中的url编码部门也要参与搜索
        if parse.quote(j).lower() in url.lower():
            flag2 += 1
    if flag1 == len(keylist):
        allList.append({'name': name, 'url': url, 'type': 1})
    elif flag2 == len(keylist):
        allList.append({'name': name, 'url': url, 'type': 2})


# 加载json文件
def loadJsonFile(route):
    with open(route, 'r', encoding='utf8') as fp:
        json_data = json.load(fp)
    return json_data


# json递归
def getUrlsInBookmarks(root, keylist):
    for i in root:
        if i['type'] != 'folder':
            url = i['url']
            name = i['name']
            AddList(bookList, url, name, keylist)
        else:
            getUrlsInBookmarks(i['children'], keylist)


def getBooks(keylist):
    bookmarks = loadJsonFile(booksDir)
    getUrlsInBookmarks(bookmarks['roots']['bookmark_bar']['children'], keylist)


def getHistory(keylist):
    # sqlite文件拷贝后使用 防止浏览器线程给文件加锁无法访问
    os.system('cp ' + historyDir + ' ' + tempDir)
    conn = sqlite3.connect(tempDir)
    cursor = conn.cursor()
    SQL = """SELECT DISTINCT(url), title, datetime((last_visit_time/1000000)-11644473600, 'unixepoch', 'localtime') 
                                        AS last_visit_time FROM urls ORDER BY last_visit_time DESC """
    cursor.execute(SQL)
    query_result = cursor.fetchall()
    cursor.close()
    conn.close()
    nameList = []
    for i in query_result:
        name = i[1]
        url = i[0]
        # 去重
        if name != '' and name in nameList:
            continue
        else:
            nameList.append(name)
        AddList(historyList, url, name, keylist)


def printResult(historyList, bookList):
    items = {"items": []}
    template = {"title": "", "subtitle": "", "arg": "", "icon": {"path": ""}}
    for i in bookList:
        template["arg"] = i['url']
        template["icon"]['path'] = 'mark.png'
        if i['type'] == 1:
            template["title"] = i['name']
            template["subtitle"] = i['url']
        if i['type'] == 2:
            template["title"] = parse.unquote(i['url'])
            template["subtitle"] = i['name']
        items["items"].append(copy.deepcopy(template))
    for i in historyList:
        template["arg"] = i['url']
        template["icon"]['path'] = 'history.png'
        if i['type'] == 1:
            template["title"] = i['name']
            template["subtitle"] = i['url']
        if i['type'] == 2:
            template["title"] = parse.unquote(i['url'])
            template["subtitle"] = i['name']
        items["items"].append(copy.deepcopy(template))
    res = json.dumps(items, ensure_ascii=False)
    print(res)
    return res


if __name__ == '__main__':
    keylist = sys.argv[1:]
    getBooks(keylist)
    getHistory(keylist)
    printResult(historyList, bookList)
