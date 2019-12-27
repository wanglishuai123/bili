# bili
# bili

哔哩哔哩爬虫，每天定时爬取关键字的所有视频信息，主要爬取的内容是一个搜索一个关键字的内容，并统计它的排名、用户名、视频信息、视频编号、点赞、播放、收藏、转发、面包屑导航等。

首先是遍历关键字的page，最多的视频是有50页，所以就是遍历50次（就算有些关键词不够50页，B站也不会报404错误，说明它的seo做的还是不错）
项目初始，就准备用队列配合多线程的方式做，并且存储到mongodb中，这样的话效率相对高。
采用MongoDB作为存储，用pymongodb操作。
Nosql比起关系型数据库真的是好用。

先解答一下具体思路：

1、遍历关键字、获取关键字的page_url，并且存放到队列中去，核心代码如下：
```python
for key in keys:
    for i in range(1,51):
        url = "https://search.bilibili.com/all?keyword={}&page={}".format(key, i)
        print(url)
        pageQ.put(url)
```

2.创建线程开始遍历每条url，获取每页下面的视频番号（B站中avxxxxx）就是番号，番号也就是视频编号，并且一并获取它的排名和根据key获取类型，并把它存储到另外的一个队列中去。
核心代码如下：

```python
class MyBili(threading.Thread):
    def __init__(self,pageQ,urlQ,key,lock):
        threading.Thread.__init__(self)
        self.urlQ = urlQ
        self.pageQ = pageQ
        self.key = key
        self.client = MongoClient(host="127.0.0.1", port=27017)
        self.collection = self.client["jihe"]["data"]  # 没有不用担心，插入数据之后就有了
        self.lock = lock
        self.headers = {}
        self.result={}
        self.headers["User-Agent"] = UserAgent().random
        self.defu =0
        
    def run(self):
        self.get_url()
        
    def get_url(self):
        print("开始av线程"+self.key)
        while True:
            if self.pageQ.empty():
                break
            lock.acquire()
            url = self.pageQ.get()
            lock.release()
            print(url)
            respone = requests.get(url,headers = self.headers)
            reg = """class="video-item matrix"><a href="//www.bilibili.com/video/av([\s\S]*?)from"""  # 正则表达式
            regex = re.compile(reg, re.IGNORECASE)  # 预编译
            respone = regex.findall(respone.text)  # 第一次正则
            for i in respone:
                data = {}
                self.defu += 1
                i = str(i).replace("?", "")
                data["id"] = self.defu
                data["key"] = self.key
                data["av"] = i
                print(data)
                urlQ.put(data)
                t1 = self.collection.insert_one(data)
                print(t1)
            urlQ.task_done()
        print("结束av线程"+self.key)
```
  3.在解析B站网页代码的时候，发现根本获取不它的数据，但它的数据的确是显示出来了呀，先打开net12，network,载刷新页面检测数据。
  并且随便搜索一个容易搜索的关键字收藏的个数，发现在最下方会有两个b站的api调用，有api能用当然是好事儿了，直接调用api就好了。
  
>  https://api.bilibili.com/x/web-interface/archive/stat?aid=17980233
  
>  https://api.bilibili.com/x/web-interface/view?aid=17980233&cid=29354691

这两个API，view中的信息较多，所以就它了，从它里面获取视频的一些信息,为了方便找层级，我给他调整了一下格式，发现除了粉丝数量没有之外，剩余的都有。

```python
{
'code': 0, 'message': '0', 'ttl': 1, 'data': 
{
        'bvid': '', 
        'aid': 17980233, 
        'videos': 1, 
        'tid': 21, 
        'tname': '日常', 
        'copyright': 1, 
        'pic': 'http://i2.hdslb.com/bfs/archive/9065be4a6a5f922d47df03aaa98164aa67cdf62a.jpg', 
        'title': '如何写好一份简历？这些奇葩错误不要犯！', 
        'pubdate': 1515146417, 'ctime': 1515146418, 
        'desc': '写简历时一定会用到，先 收藏 ↓',
        'state': 0, 'attribute': 49280, 
        'duration': 608, 'rights': {'bp': 0, 'elec': 0, 'download': 1, 'movie': 0, 'pay': 0, 'hd5': 0, 'no_reprint': 1, 'autoplay': 1, 'ugc_pay': 0, 'is_cooperation': 0, 'ugc_pay_preview': 0, 'no_background': 0}, 
        'owner': {'mid': 23379333, 'name': '许捷许仙僧', 'face': 'http://i2.hdslb.com/bfs/face/eb307a3f7ebd6735996c97e922621d86970cf4aa.jpg'}, 
        'stat': {'aid': 17980233, 'view': 153744, 'danmaku': 634, 'reply': 315, 'favorite': 14399, 'coin': 4055, 'share': 1949, 'now_rank': 0, 'his_rank': 0, 'like': 4038, 'dislike': 0, 'evaluation': ''}, 
        'dimension': {'width': 0, 'height': 0, 'rotate': 0}, 'no_cache': False, 
        'pages': [{'cid': 29354691, 'page': 1, 'from': 'vupload', 'part': '', 'duration': 608, 'vid': '', 'weblink': '', 'dimension': {'width': 0, 'height': 0, 'rotate': 0}}], 
        'subtitle': {'allow_submit': False, 'list': []}
    }
}
```
核心代码如下：

```python
class Get_url(threading.Thread):
    def __init__(self,urlQ,dataQ,sheet):
        threading.Thread.__init__(self)
        self.headers = {}
        self.result = {}
        self.sheet = sheet
        self.urlQ = urlQ
        self.dataQ = dataQ
        self.client = MongoClient(host="127.0.0.1", port=27017)
        self.collection = self.client["shuju"]["wanglishuai"]  # 没有不用担心，插入数据之后就有了
        self.headers["User-Agent"] = UserAgent().random

    def run(self):
        self.test_get()
    def test_get(self):
        print("开始api线程")

        while True:
            if self.urlQ.empty():
                break
            i = self.urlQ.get()
            url = "http://api.bilibili.com/x/web-interface/view?aid={}".format(i["av"])  # 视频信息api
            req = requests.get(url, headers=self.headers).json()
            time.sleep(1)
            lock.acquire()
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
            self.result["category_1"] = ""
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
                self.collection = self.client["shuju"]["模板"]
            else:
                self.collection = self.client["shuju"]["qita"]
            lock.release()

            sex = self.collection.insert_one(self.result)
            self.dataQ.put(self.result)
            self.dataQ.task_done()
            print(sex)

        print("结束api线程")

```
