# PROJECT : bili
# AUTHOR  : WangLishuai
# TIME    : 2019-12-26 21:31
# FILE    : Get_url
import time

import requests
from pymongo import MongoClient
from fake_useragent import UserAgent
import queue
import threading
import xlwt
import re
from lxml import etree
# 程序开始
start = time.time()


# 获取番号类
class Get_url(threading.Thread):

    def __init__(self,pageQ,urlQ,key,lock):
        threading.Thread.__init__(self)
        self.urlQ = urlQ
        self.pageQ = pageQ
        self.key = key
        self.lock = lock
        self.headers = {}
        self.result={}
        self.headers["User-Agent"] = UserAgent().random
        self.defu =0

    def run(self):
        print("开始av线程"+self.key)
        self.get_video_info()
        print("结束av线程"+self.key)

    def get_video_info(self):
        while True:
            if self.pageQ.empty():
                break
            self.lock.acquire()
            url = self.pageQ.get()
            print(url)
            respones = requests.get(url,headers = self.headers)
            time.sleep(1)
            reg = """class="video-item matrix"><a href="//www.bilibili.com/video/av([\s\S]*?)from"""  # 正则表达式
            regex = re.compile(reg, re.IGNORECASE)  # 预编译
            res = regex.findall(respones.text)  # 第一次正则
            print(res)

            #获取番号(视频编号)
            for i in res:
                data = {}
                self.defu += 1
                i = str(i).replace("?", "")
                data["id"] = self.defu
                data["key"] = self.key
                data["av"] = i
                print(data)
                urlQ.put(data)
            self.lock.release()
            urlQ.task_done()


# 获取视频信息

class Get_video_info(threading.Thread):

    def __init__(self,urlQ):
        threading.Thread.__init__(self)
        self.headers = {}
        self.result = {}
        self.urlQ = urlQ
        self.client = MongoClient(host="127.0.0.1", port=27017)
        self.headers["User-Agent"] = UserAgent().random

    def run(self):
        self.test_get()
        
    # 获取视频信息
    def test_get(self):
        print("开始api线程")

        while True:
            if self.urlQ.empty():
                break
            lock.acquire()
            i = self.urlQ.get()
            url = "http://api.bilibili.com/x/web-interface/view?aid={}".format(i["av"])  # 视频信息api
            respone = requests.get("https://www.bilibili.com/video/av{}".format(i["av"])).text
            html = etree.HTML(respone)
            cotegory1 = html.xpath('//span[@class="a-crumbs"]/a')[0].text
            req = requests.get(url, headers=self.headers).json()
            time.sleep(1) # 延时一秒，太快会限制ip访问,会导致线程阻塞
            data = req["data"]
            owner = data["owner"]
            stat = data["stat"]
            self.result={}
            self.result["search_terms"] = i["key"]  # 搜索词
            self.result["search_rank"] = i["id"]  # 搜索排名
            self.result["up_id"] = owner["mid"]  # up主id
            self.result["up_username"] = owner["name"]  # up主用户名
            self.result["video_url"] = "https://www.bilibili.com/video/{}".format(i["av"])  # 视频链接
            self.result["video_name"] = data["title"]  # 视频名称
            self.result["vide_published_at"] = data["ctime"]  # 发布时间
            self.result["video_playback_num"] = stat["view"]  # 播放量
            self.result["video_barrage_num"] = stat["danmaku"]  # 弹幕
            self.result["video_like_num"] = stat["like"]  # 点赞
            self.result["video_coin_num"] = stat["coin"]  # 投币
            self.result["video_favorite_num"] = stat["favorite"]  # 收藏
            self.result["video_forward_num"] = stat["share"]  # 转发 8项
            self.result["category_1"] = cotegory1
            self.result["category_2"] = data["tname"]  # 分区2
            url3 = "https://api.bilibili.com/x/web-interface/card?mid={}".format(self.result["up_id"])  # 作者信息api
            req = requests.get(url3, headers=self.headers).json()
            data = req["data"]["card"]
            if data["mid"] != "--":
                self.result["up_follow_num"] = data["fans"]
            print(self.result)
            if i["key"]=="简历":
                self.collection=self.client["shuju"]["简历"]
            elif i["key"]=="简历模板":
                self.collection = self.client["shuju"]["简历模板"]
            elif i["key"]=="找工作":
                self.collection = self.client["shuju"]["找工作"]
            elif i["key"]=="实习":
                self.collection = self.client["shuju"]["实习"]
            elif i["key"]=="笔试":
                self.collection = self.client["shuju"]["笔试"]
            elif i["key"]=="职场":
                self.collection = self.client["shuju"]["职场"]
            elif i["key"]=="面试":
                self.collection = self.client["shuju"]["面试"]
            else:
                self.collection = self.client["shuju"]["other"]
            lock.release()
            sex = self.collection.insert_one(self.result)
            print(sex)
        print("结束api线程")

class Save_excel():
    def __init__(self):
        self.book = xlwt.Workbook(encoding="utf-8")
        self.t1 = {"search_terms": "笔试", "search_rank": 19, "up_id": 471801158, "up_username": "路飞学城小媛老师",
                          "video_url": "https://www.bilibili.com/video/80572356", "video_name": "[案例篇] 使用python自动生成word简历",
                          "vide_published_at": 1577264427, "video_playback_num": 49, "video_barrage_num": 0,
                          "video_like_num": 4,
                          "video_coin_num": 2, "video_favorite_num": 7, "video_forward_num": 0, "category_1": "",
                          "category_2": "演讲• 公开课", "up_follow_num": 1260}
    def test_get(self,key,collection):
            datas = collection.find()
            print("正在生成"+key+".xls...")
            # 增加一个sheet
            sheet = self.book.add_sheet(key, cell_overwrite_ok=True)
            # 写表头
            num = 0
            for i in self.t1:
                sheet.write(0, num, i)
                num += 1
            #写数据
            line = 1
            for data in datas:
                num = 0
                for i in data.items():
                    if i[0]=="_id":
                        continue
                    sheet.write(line,num,i[1])
                    num+=1
                line+=1
            self.book.save(key+".xls")
            print("生成"+key+".xls表成功！")
            print("--------------------")


# 关键字
# keys = ["简历", "简历模板","面试", "实习", "找工作", "笔试", "职场"]
keys = ["简历", "简历模板"]

# 创建队列
pageQ = queue.Queue()
urlQ = queue.Queue()
lock = threading.Lock()
get_urls = []
get_video_infos = []

# 开始执行获取page、番号
for key in keys:
    for i in range(1,51):
        url = "https://search.bilibili.com/all?keyword={}&page={}".format(key, i)
        print(url)
        pageQ.put(url)
    get_url = Get_url(pageQ,urlQ,key,lock)
    get_url.start()
    get_urls.append(get_url)

#延时10秒
time.sleep(10)


for key in keys:
    get_video_info = Get_video_info(urlQ)
    get_video_info.start()
    get_video_infos.append(get_video_info)

#线程等待
for t in get_urls:
    t.join()
for t in get_video_infos:
    t.join()


# 实例化存储Excel类
save = Save_excel()
client = MongoClient(host="127.0.0.1", port=27017)
# 开始读取mongodb，生成excel
for key in keys:
    collection = client["shuju"][key]
    save.test_get(key,collection)

end = time.time()
print("程序结束，共使用："+str(end-start)+"秒")







