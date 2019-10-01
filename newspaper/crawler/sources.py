from torequests.utils import quote_plus
import sys
import pathlib
sys.path.append(str(pathlib.Path(__file__).absolute().parent.parent))
from config import ONLINE_HOST

content_sources = [
    {
        "title": "Python Software Foundation News",
        "url": "https://pyfound.blogspot.com/",
        "level": 4,
        "lang": "EN",
        "status": "√",
        "desc": "[墙] 来自 Python 软件基金会的消息"
    },
    {
        "title": "Python Weekly",
        "url": "https://www.pythonweekly.com/",
        "level": 5,
        "lang": "EN",
        "status": "√",
        "desc": "必备周报"
    },
    {
        "title": "PyCoder's Weekly",
        "url": "https://pycoders.com/issues",
        "level": 5,
        "lang": "EN",
        "status": "√",
        "desc": "必备周报"
    },
    {
        "title": "Import Python",
        "url": "https://importpython.com/newsletter/archive/",
        "level": 5,
        "lang": "EN",
        "status": "√",
        "desc": "必备周报, 2019.1.11 停更了, 希望早日康复~"
    },
    {
        "title": "Awesome Python Newsletter",
        "url": "https://python.libhunt.com/newsletter/archive",
        "level": 5,
        "lang": "EN",
        "status": "√",
        "desc": "必备周报"
    },
    {
        "title": "Real Python",
        "url": "https://realpython.com/",
        "level": 4,
        "lang": "EN",
        "status": "√",
        "desc": "文章质量高, 更新较少"
    },
    {
        "title": "Planet Python",
        "url": "https://planetpython.org",
        "level": 3,
        "lang": "EN",
        "status": "√",
        "desc": "官方推荐的博客, 收录了很多博主"
    },
    {
        "title": "Julien Danjou",
        "url": "https://julien.danjou.info",
        "level": 4,
        "lang": "EN",
        "status": "√",
        "desc": "文章质量不错, 保持更新"
    },
    {
        "title": "Doug Hellmann",
        "url": "https://doughellmann.com/blog/",
        "level": 4,
        "lang": "EN",
        "status": "√",
        "desc": "大名鼎鼎, 文章质量很高"
    },
    {
        "title": "The Mouse Vs. The Python",
        "url": "https://www.blog.pythonlibrary.org",
        "level": 4,
        "lang": "EN",
        "status": "√",
        "desc": "文章质量不错"
    },
    {
        "title": "InfoQ",
        "url": "https://www.infoq.cn/topic/python",
        "level": 4,
        "lang": "CN",
        "status": "√",
        "desc": "原创/译文的质量不错"
    },
    {
        "title": "Jeff Knupp",
        "url": "https://jeffknupp.com/",
        "level": 4,
        "lang": "EN",
        "status": "X",
        "desc": "[墙] 热门博客, 2018以后不更新了, 并且 planetpython 有, 暂不收录"
    },
    {
        "title": "Hacker News",
        "url": "https://hn.algolia.com/?query=python&sort=byPopularity&prefix&page=0&dateRange=last24h&type=story",
        "level": 4,
        "lang": "EN",
        "status": "√",
        "desc": "大名鼎鼎的 HN"
    },
    {
        "title": "Python Insider",
        "url": "https://blog.python.org/",
        "level": 3,
        "lang": "EN",
        "status": "X",
        "desc": "官方开发进度, 被官博和 planetPython 包含, 所以不需要收录."
    },
    {
        "title": "Brett Cannon",
        "url": "https://snarky.ca/",
        "level": 3,
        "lang": "EN",
        "status": "√",
        "desc": "核心开发者"
    },
    {
        "title": "Encode",
        "url": "https://www.encode.io/",
        "level": 3,
        "lang": "EN",
        "status": "X",
        "desc": "知名 Python 开源组织, 文章太少, 暂不收录"
    },
    {
        "title": "机器之心",
        "url": "https://www.jiqizhixin.com/search/article?keywords=python&search_internet=true&sort=time",
        "level": 3,
        "lang": "CN",
        "status": "√",
        "desc": "知名公众号"
    },
    {
        "title": "依云's Blog",
        "url": "https://blog.lilydjwg.me/tag/python?page=1",
        "level": 3,
        "lang": "CN",
        "status": "√",
        "desc": "文章质量很高"
    },
    {
        "title": "DEV Community",
        "url": "https://dev.to/t/python/latest",
        "level": 3,
        "lang": "EN",
        "status": "√",
        "desc": "算是个挺好的社区, post 也都不太水"
    },
    {
        "title": "Python猫",
        "url": "https://zhuanlan.zhihu.com/pythonCat",
        "level": 3,
        "lang": "CN",
        "status": "√",
        "desc": "2018 年末比较热情的博主, 原创"
    },
    {
        "title": "Python之美",
        "url": "https://zhuanlan.zhihu.com/python-cn",
        "level": 3,
        "lang": "CN",
        "status": "√",
        "desc": "早期文章较多, 创业以后更新不太多了"
    },
    {
        "title": "静觅",
        "url": "https://cuiqingcai.com/category/technique/python",
        "level": 3,
        "lang": "CN",
        "status": "√",
        "desc": " 崔庆才的个人博客, 保持更新的原创博主"
    },
    {
        "title": "推酷(中文)",
        "url": "https://www.tuicool.com/topics/11130000?st=0&lang=1",
        "level": 3,
        "lang": "CN",
        "status": "√",
        "desc": "推文类站点. 按热门排序"
    },
    {
        "title": "推酷(英文)",
        "url": "https://www.tuicool.com/topics/11130000?st=0&lang=2",
        "level": 3,
        "lang": "EN",
        "status": "√",
        "desc": "推文类站点. 按热门排序"
    },
    {
        "title": "开发者头条",
        "url": "https://toutiao.io/tags/python?type=latest",
        "level": 3,
        "lang": "CN",
        "status": "X",
        "desc": "推文类站点, 但是没有发布时间, 暂不收录"
    },
    {
        "title": "稀土掘金",
        "url": "https://juejin.im/tag/Python",
        "level": 3,
        "lang": "CN",
        "status": "√",
        "desc": "推文类站点. 按热门排序"
    },
    {
        "title": "Python部落",
        "url": "https://python.freelycode.com/contribution/list/0?page_no=1",
        "level": 3,
        "lang": "CN",
        "status": "√",
        "desc": "推文+译文"
    },
    {
        "title": "miguelgrinberg",
        "url": "https://blog.miguelgrinberg.com/index",
        "level": 3,
        "lang": "EN",
        "status": "√",
        "desc": "Web 开发相关的内容挺多, 质量较高"
    },
    {
        "title": "Ned Batchelder",
        "url": "https://nedbatchelder.com/blog/tag/python.html",
        "level": 3,
        "lang": "EN",
        "status": "√",
        "desc": "热门博主。planetpython 也有"
    },
    {
        "title": "Full Stack Python",
        "url": "https://www.fullstackpython.com/blog.html",
        "level": 3,
        "lang": "EN",
        "status": "X",
        "desc": "热门博主。planetpython 有了, 文章比较少, 暂不收录"
    },
    {
        "title": "Eli Bendersky's website",
        "url": "https://eli.thegreenplace.net/tag/python",
        "level": 3,
        "lang": "EN",
        "status": "X",
        "desc": "值得一看，planetpython 有, 暂不收录"
    },
    {
        "title": "Manjusaka",
        "url": "https://manjusaka.itscoder.com/tags/Python/",
        "level": 3,
        "lang": "CN",
        "status": "X",
        "desc": "原创还不错, 但是文章较少, 暂不收录"
    },
    {
        "title": "Python程序员",
        "url": "https://zhuanlan.zhihu.com/pythoncxy",
        "level": 3,
        "lang": "CN",
        "status": "√",
        "desc": "关注破万的知乎专栏"
    },
    {
        "title": "Python头条",
        "url": "https://zhuanlan.zhihu.com/c_111369541",
        "level": 3,
        "lang": "CN",
        "status": "√",
        "desc": "关注破万的知乎专栏"
    },
    {
        "title": "the5fire的技术博客",
        "url": "https://www.the5fire.com/category/python/",
        "level": 3,
        "lang": "CN",
        "status": "√",
        "desc": "保持更新的热门中文博主"
    },
    {
        "title": "Python之禅",
        "url": "https://foofish.net/",
        "level": 3,
        "lang": "CN",
        "status": "√",
        "desc": "文章较基础, 质量不错"
    },
    {
        "title": "V2EX",
        "url": "https://www.v2ex.com/go/python",
        "level": 3,
        "lang": "CN",
        "status": "X",
        "desc": "社区类, api 失效, web 端乱七八糟的, 不收录"
    },
    {
        "title": "伯乐在线",
        "url": "http://python.jobbole.com/all-posts/",
        "level": 3,
        "lang": "CN",
        "status": "X",
        "desc": "有点类似推酷, 质量参差不齐. HTTP ERROR 503"
    },
    {
        "title": "Python 3 Module of the Week",
        "url": "https://pymotw.com/3/",
        "level": 3,
        "lang": "EN",
        "status": "X",
        "desc": "看起来不怎么更新了, 暂不收录"
    },
    {
        "title": "The Invent with Python Blog",
        "url": "https://inventwithpython.com/blog/index.html",
        "level": 3,
        "lang": "EN",
        "status": "√",
        "desc": "感觉不错"
    },
    {
        "title": "Armin Ronacher's Thoughts and Writings",
        "url": "http://lucumr.pocoo.org/",
        "level": 3,
        "lang": "EN",
        "status": "√",
        "desc": "Flask 作者 Armin Ronacher"
    },
    {
        "title": "aio-libs",
        "url": "https://groups.google.com/forum/#!forum/aio-libs",
        "level": 3,
        "lang": "EN",
        "status": "X",
        "desc": "知名 Python 开源组织, 不过没有文章类的 post"
    },
    {
        "title": "码农周刊",
        "url": "https://weekly.manong.io/issues/",
        "level": 3,
        "lang": "CN",
        "status": "X",
        "desc": "课外读物, 非 Python 主题, 暂不收录"
    },
    {
        "title": "编程派",
        "url": "http://codingpy.com/",
        "level": 3,
        "lang": "CN",
        "status": "√",
        "desc": "原创+译文"
    },
    {
        "title": "峰云's blog",
        "url": "http://xiaorui.cc/category/python/",
        "level": 3,
        "lang": "CN",
        "status": "X",
        "desc": "起码是个原创的, 很久不更了, 暂不收录"
    },
    {
        "title": "Dan Bader",
        "url": "https://dbader.org/blog/",
        "level": 3,
        "lang": "EN",
        "status": "X",
        "desc": "一年不更新了, 先不收录了"
    },
    {
        "title": "Pythonic Perambulations",
        "url": "https://jakevdp.github.io/",
        "level": 3,
        "lang": "EN",
        "status": "X",
        "desc": "最后更新 Thu 13 September 2018, 暂不收录"
    },
    {
        "title": "开源中国翻译",
        "url": "https://www.oschina.net/translate/tag/python",
        "level": 3,
        "lang": "CN",
        "status": "X",
        "desc": "入库留着吧, 估计不更了, 暂不收录"
    },
    {
        "title": "Trey Hunner",
        "url": "https://treyhunner.com/blog/archives/",
        "level": 3,
        "lang": "EN",
        "status": "√",
        "desc": "Help developers level-up their Python skills"
    },
    {
        "title": "Python Central",
        "url": "https://www.pythoncentral.io/",
        "level": 3,
        "lang": "EN",
        "status": "X",
        "desc": "不更新了, 暂不收录"
    },
    {
        "title": "Inside the Head of PyDanny",
        "url": "https://www.pydanny.com/",
        "level": 3,
        "lang": "EN",
        "status": "X",
        "desc": "不更新了, 暂不收录"
    },
    {
        "title": "华蟒用户组,CPyUG",
        "url": "https://groups.google.com/forum/#!forum/python-cn",
        "level": 3,
        "lang": "EN",
        "status": "X",
        "desc": "[墙] 社区类, 自己看看就好, 暂不收录"
    },
    {
        "title": "Treehl",
        "url": "https://family-treesy.github.io/tags/PYTHON/",
        "level": 3,
        "lang": "CN",
        "status": "X",
        "desc": "文章较基础, 久不更新, 暂不收录"
    },
    {
        "title": "蠎周刊",
        "url": "http://weekly.pychina.org",
        "level": 3,
        "lang": "CN",
        "status": "X",
        "desc": "官网已挂, 实际是那些周刊的译文"
    },
    {
        "title": "zzzeek",
        "url": "https://techspot.zzzeek.org/",
        "level": 3,
        "lang": "EN",
        "status": "X",
        "desc": "2016 年后停更了"
    },
    {
        "title": "Yu’s blog",
        "url": "https://gofisher.github.io/",
        "level": 3,
        "lang": "CN",
        "status": "X",
        "desc": "原创, 但是久不更新了, 网站 http://blog.rainy.im/ 挂了"
    },
    {
        "title": "程序师",
        "url": "http://www.techug.com/tag/python",
        "level": 3,
        "lang": "CN",
        "status": "X",
        "desc": "原创较少, 文章较旧"
    },
    {
        "title": "一根笨茄子",
        "url": "http://blog.guoyb.com/tags/Python/",
        "level": 3,
        "lang": "CN",
        "status": "X",
        "desc": "文章更新较少, 质量参差"
    },
    {
        "title": "追梦人物",
        "url": "https://www.zmrenwu.com/",
        "level": 2,
        "lang": "CN",
        "status": "X",
        "desc": "像个学习博客"
    },
    {
        "title": "anshengme",
        "url": "https://blog.ansheng.me/",
        "level": 2,
        "lang": "CN",
        "status": "X",
        "desc": "质量一般"
    },
    {
        "title": "Pegasus",
        "url": "http://ningning.today/categories/python/",
        "level": 2,
        "lang": "CN",
        "status": "X",
        "desc": "不怎么更新"
    },
    {
        "title": "FunHacks",
        "url": "https://funhacks.net/categories/Python/",
        "level": 2,
        "lang": "CN",
        "status": "X",
        "desc": "太久不更新了, 不过python 之旅还行"
    },
    {
        "title": "Peter Norvig's essays",
        "url": "http://norvig.com/",
        "level": 2,
        "lang": "EN",
        "status": "X",
        "desc": "这排版驾驭不了..."
    },
    {
        "title": "Peterbe.com",
        "url": "https://www.peterbe.com/plog/",
        "level": 2,
        "lang": "EN",
        "status": "X",
        "desc": "不是太值得收录"
    },
    {
        "title": "Python Tips",
        "url": "https://pythontips.com/",
        "level": 2,
        "lang": "EN",
        "status": "X",
        "desc": "很火, 但我不喜欢"
    },
    {
        "title": "脚本之家",
        "url": "https://www.jb51.net/list/list_97_1.htm",
        "level": 2,
        "lang": "CN",
        "status": "X",
        "desc": "文章的质量啊~~~"
    },
    {
        "title": "开源中国搜索",
        "url": "https://www.oschina.net/search?scope=translate&q=python&category=0&onlytitle=0&sort_by_time=1",
        "level": 2,
        "lang": "CN",
        "status": "X",
        "desc": "质量不太高"
    },
    {
        "title": "伯乐在线头条",
        "url": "http://top.jobbole.com/tag/python/?sort=latest",
        "level": 2,
        "lang": "CN",
        "status": "X",
        "desc": "停更"
    },
    {
        "title": "代码片段",
        "url": "http://www.phpxs.com/code/python",
        "level": 2,
        "lang": "CN",
        "status": "X",
        "desc": "文章太老了, 停更了"
    },
    {
        "title": "segmentfault",
        "url": "https://segmentfault.com/t/python/blogs",
        "level": 2,
        "lang": "CN",
        "status": "X",
        "desc": "文章质量"
    },
    {
        "title": "Python China",
        "url": "http://python-china.org/api/topics/timeline",
        "level": 2,
        "lang": "CN",
        "status": "X",
        "desc": "欠费网站挂了"
    },
    {
        "title": "麦穗技术",
        "url": "http://www.58maisui.com/category/python/",
        "level": 2,
        "lang": "CN",
        "status": "X",
        "desc": "网站挂了"
    },
    {
        "title": "CSDN",
        "url": "https://so.csdn.net/so/search/s.do?q=python&t=blog&u=",
        "level": 1,
        "lang": "CN",
        "status": "X",
        "desc": "文章质量啊~~~"
    },
    {
        "title": "Stack Overflow",
        "url": "https://stackoverflow.com/?tab=hot",
        "level": 3,
        "lang": "EN",
        "status": "X",
        "desc": "已解决 + python + vote>=5, 但是问题有点弱智, 暂不收录"
    },
    {
        "title": "Reddit",
        "url": "https://www.reddit.com/r/Python/top/",
        "level": 3,
        "lang": "EN",
        "status": "√",
        "desc": "知名社区. 质量参差, 收录每日 ups>=20"
    },
]

content_sources_dict = {i['title']: i for i in content_sources}


def main():
    import pathlib
    import re
    # =: 待收录, √: 已收录, X: 不收录, -: 入库不追更

    titles = [i['title'] for i in content_sources]
    # 确保没有重复的
    if len(titles) != len(set(titles)):
        raise RuntimeError('不能有重复的 title')
    if '|' in str(content_sources):
        raise RuntimeError('尽量不要有 |')

    providers = ''
    providers += '| 序号 | 名称 | 评分 | 语言 | 收录 | 描述 |\n'
    providers += '| ---- | ---- | ---- | ---- | ---- | ---- |\n'
    todo_counts = 0
    finish_counts = 0
    for x, item in enumerate(content_sources, 1):
        data = [str(x)]
        title_link = f'[{item["title"]}]({item["url"]})'
        data.append(title_link)
        data.append(str(item['level']))
        data.append(item['lang'])
        status = item['status']
        if item['status'] == '√':
            finish_counts += 1
            status = f'[√](https://{ONLINE_HOST}/newspaper/articles.query.html?source={quote_plus(item["title"])})'
        elif item['status'] == '=':
            todo_counts += 1
        data.append(status)
        data.append(item['desc'])
        string = ' | '.join(data)
        providers += '| ' + string + ' |\n'
    proc = f'* 收录进度: {finish_counts} / {finish_counts + todo_counts}\n\n\t> = 待收录  |  √ 已收录  |  X 不收录  |  - 入库不追更\n\n'
    README_FP = pathlib.Path(__file__).absolute().parent.parent.parent / 'README.md'
    with README_FP.open('r', encoding='u8') as f:
        old = f.read()
        new = re.sub(
            '<!-- providers start -->[\s\S]*?<!-- providers end -->',
            f'<!-- providers start -->\n\n{proc}{providers}\n\n<!-- providers end -->',
            old)
        print(new)
    with README_FP.open('w', encoding='u8') as f:
        f.write(new)


if __name__ == "__main__":
    main()
