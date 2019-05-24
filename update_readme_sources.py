import re

from newspaper.crawler.sources import content_sources

# =: 待收录, √: 已收录, X: 不收录, -: 入库不追更
status_colors = {
    '=': '<span style="color: orange">=</span>',
    '√': '<span style="color: green">√</span>',
    'X': '<span style="color: red">X</span>',
    '-': '<span style="color: black">-</span>',
}


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
    todo_counts = 0
    finish_counts = 0
    for x, item in enumerate(content_sources, 1):
        data = [str(x)]
        title_link = f'[{item["title"]}]({item["url"]})'
        data.append(title_link)
        data.append(str(item['level']))
        data.append(item['lang'])
        if item['status'] == '√':
            finish_counts += 1
        elif item['status'] == '=':
            todo_counts += 1
        data.append(status_colors.get(item['status'], item['status']))
        data.append(item['desc'])
        string = ' | '.join(data)
        providers += '| ' + string + ' |\n'
    proc = f'* 收录进度: {finish_counts} / {finish_counts + todo_counts}\n\n\t> = 待收录  |  √ 已收录  |  X 不收录  |  - 入库不追更\n\n'
    with open('README.md', 'r', encoding='u8') as f:
        old = f.read()
        new = re.sub(
            '<!-- providers start -->[\s\S]*?<!-- providers end -->',
            f'<!-- providers start -->\n\n{proc}{providers}\n\n<!-- providers end -->',
            old)
        # print(new)
    with open('README.md', 'w', encoding='u8') as f:
        f.write(new)


if __name__ == "__main__":
    main()
