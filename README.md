# bili
哔哩哔哩爬虫，每天定时爬取关键字的所有视频信息，主要爬取的内容是一个搜索一个关键字的内容，并统计它的排名、用户名、视频信息、视频编号、点赞、播放、收藏、转发、面包屑导航等。

首先是遍历关键字的page，最多的视频是有50页，所以就是遍历50次（就算有些关键词不够50页，B站也不会报404错误，说明它的seo做的还是不错）
项目初识我就准备用队列配合多线程的方式做，这样的话效率相对高，虽然python的多线程的确比较鸡肋。

先解答一下具体思路：

1、遍历关键字、获取关键字的page_url，并且存放到队列中去，核心代码如下：

for key in keys:
    for i in range(1,51):
        url = "https://search.bilibili.com/all?keyword={}&page={}".format(key, i)
        print(url)
        pageQ.put(url)

2.创建线程开始遍历每条url，获取每页下面的视频番号（B站中avxxxxx）就是番号，番号也就是视频编号，并且一并获取它的排名和根据key获取类型，并把它存储到另外的一个队列中去。
核心代码如下：

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
  3.在解析B站网页代码的时候，发现根本获取不它的数据，但它的数据的确是显示出来了呀，先打开net12，network,载刷新页面检测数据。
  并且随便搜索一个容易搜索的关键字
  

  
