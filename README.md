# 哔哩哔哩指定词汇爬虫
> 哔哩哔哩爬虫，每天定时爬取所定义关键字的所有视频信息，主要爬取的内容是排名、用户名、用户账号、视频信息、视频编号、点赞、播放、收藏、转发、面包屑导航等(类型)、发布时间、。

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
            url = self.pageQ.get()
            print(url)
            respones = requests.get(url,headers = self.headers)
            time.sleep(1)
            reg = """class="video-item matrix"><a href="//www.bilibili.com/video/av([\s\S]*?)from"""  # 正则表达式
            regex = re.compile(reg, re.IGNORECASE)  # 预编译
            res = regex.findall(respones.text)  # 第一次正则
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
                urlQ.task_done()
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
            #获取第一个分区
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
```
下一步就是把存储到MongoDB中的数据，写到excel表中，这儿我本来想从队列中区数据，再配合多线程的方式添加数据进去，但是经过很多次的尝试，发现效果并没有直接从MongoDB来的快，几乎没多少秒就搞定了。

```python
#生成Excel表
class Save_excel():
    def __init__(self):
        self.book = xlwt.Workbook(encoding="utf-8")
        # 这儿是直接随便取了一个API的信息，获取其键，作为生成表头的数据
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
                    # 跳过ID_栏
                    if i[0]=="_id":
                        continue
                    sheet.write(line,num,i[1])
                    num+=1
                line+=1
            self.book.save(key+".xls")
            print("生成"+key+".xls表成功！")
            print("--------------------")
```

主要文件已经上传到Github中了，欢迎大家指正。
