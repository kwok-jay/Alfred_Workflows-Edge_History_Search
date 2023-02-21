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
historyList = []
# 集锦存在位置
collectionDir = '/Users/kwok-jay/Library/Application\ Support/Microsoft\ Edge/Default/Collections/collectionsSQLite'
collectionList = []
collectionClasses = []
# 指定一个历史记录缓存位置 避免database is locked
tempHistory = './history'
tempCollection = './collection'


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
    if flag1 == len(keylist):  # 命中了name
        allList.append({'name': name, 'url': url, 'type': 1})
    elif flag2 == len(keylist):  # 命中了url
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
    os.system('cp ' + historyDir + ' ' + tempHistory)
    conn = sqlite3.connect(tempHistory)
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


def getCollections(keylist, pid=''):
    # sqlite文件拷贝后使用 防止浏览器线程给文件加锁无法访问
    os.system('cp ' + collectionDir + ' ' + tempCollection)
    conn = sqlite3.connect(tempCollection)
    cursor = conn.cursor()
    if pid == '':
        SQL = 'SELECT source,title FROM items'
    else:
        SQL = """SELECT a.source,a.title,b.parent_id 
        FROM (SELECT id,title,source FROM items) AS a 
        LEFT JOIN collections_items_relationship as b on a.id=b.item_id 
        WHERE parent_id='{}'""".format(str(pid))
    # SQL = """SELECT c.title,c.source,d.title as p_title FROM
    #         (SELECT a.title,a.source,b.parent_id FROM
    #         (SELECT id,title,source FROM items) AS a LEFT JOIN collections_items_relationship as b on a.id=b.item_id) as c
    #         LEFT JOIN collections as d on c.parent_id=d.id"""
    cursor.execute(SQL)
    query_result = cursor.fetchall()
    cursor.close()
    conn.close()
    nameList = []
    for i in query_result:
        url = i[0]
        if len(url) > 0:
            url = json.loads(url.decode())['url']
        else:
            continue
        name = i[1]
        # 去重
        if name != '' and name in nameList:
            continue
        else:
            nameList.append(name)
        if pid == '':
            AddList(collectionList, url, name, keylist)
        else:
            collectionList.append({'name': name, 'url': url, 'type': 1})


def getCollectionsClasses(keylist):
    conn = sqlite3.connect(tempCollection)
    cursor = conn.cursor()
    SQL = 'SELECT id,title FROM collections'
    cursor.execute(SQL)
    query_result = cursor.fetchall()
    cursor.close()
    conn.close()
    for i in query_result:
        id = i[0]
        name = i[1]
        flag = 0
        # 多个关键词同时在名称中包含 或者 多个关键词同时在url中包含
        for j in keylist:
            if j.lower() in name.lower():
                flag += 1
        if flag == len(keylist):
            collectionClasses.append({
                'name': name,
                'url': id,
                'type': 0,
            })


def printResult(dataList):
    items = {"items": []}
    template = {"title": "", "subtitle": "", "arg": "", "icon": {"path": ""}}
    for icon, datas in dataList:
        for i in datas:
            template["arg"] = i['url']
            template["icon"]['path'] = icon
            if i['type'] == 0:
                template["title"] = i['name']
                template["subtitle"] = '打开合集[' + i['name'] + ']'
                template["arg"] = 'collection,' + i['url']
            if i['type'] == 1:  # 优先显示name还是url
                template["title"] = i['name']
                template["subtitle"] = i['url']
            if i['type'] == 2:
                template["title"] = parse.unquote(i['url'])
                template["subtitle"] = i['name']
            items["items"].append(copy.deepcopy(template))
    print(json.dumps(items, ensure_ascii=False))


if __name__ == '__main__':
    keylist = sys.argv[1:]
    if keylist[0].startswith('collection,'):
        getCollections(keylist, pid=keylist[0][11:])
        printResult([('collection.png', collectionList)])
    else:
        getBooks(keylist)
        getHistory(keylist)
        getCollections(keylist)
        getCollectionsClasses(keylist)
        printResult([('class.png', collectionClasses), ('mark.png', bookList),
                     ('collection.png', collectionList),
                     ('history.png', historyList)])
