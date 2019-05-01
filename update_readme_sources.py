import re

from newspaper.crawler.sources import content_sources


def main():
    titles = [i['title'] for i in content_sources]
    # 确保没有重复的
    if len(titles) != len(set(titles)):
        raise RuntimeError('不能有重复的 title')
    if '|' in str(content_sources):
        raise RuntimeError('尽量不要有 |')

    providers = ''
    providers += '| 序号 | 名称 | 评分 | 语言 | 收录 | 描述 |\n'
    providers += '| ---- | ---- | ---- | ---- | ---- | ---- |\n'

    for x, item in enumerate(content_sources, 1):
        data = [str(x)]
        title_link = f'[{item["title"]}]({item["url"]})'
        data.append(title_link)
        data.append(item['level'])
        data.append(item['lang'])
        data.append(item['status'])
        data.append(item['desc'])
        string = ' | '.join(data)
        providers += '| ' + string + ' |\n'
    with open('README.md', 'r', encoding='u8') as f:
        old = f.read()
        new = re.sub(
            '<!-- providers start -->[\s\S]*?<!-- providers end -->',
            '<!-- providers start -->\n\n%s\n\n<!-- providers end -->' %
            providers, old)
        # print(new)
    with open('README.md', 'w', encoding='u8') as f:
        f.write(new)


if __name__ == "__main__":
    main()
