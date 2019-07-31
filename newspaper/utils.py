import aiofiles
from torequests.utils import escape


async def tail_file(fp, size=100):
    current_seek = 0
    async with aiofiles.open(fp, encoding='u8', errors='ignore') as f:
        while 1:
            await f.seek(current_seek)
            text = await f.read(1)
            if not text:
                stop_pos = current_seek - size * 2
                break
            current_seek += size
        if stop_pos < 0:
            stop_pos = 0
        await f.seek(stop_pos)
        text = (await f.read())[-size:]
        return text


def gen_rss(data):
    nodes = []
    channel = data['channel']
    channel_title = channel['title']
    channel_desc = channel['description']
    channel_link = channel['link']
    channel_language = channel.get('language', 'zh-cn')
    item_keys = ['title', 'description', 'link', 'guid', 'pubDate']
    for item in data['items']:
        item_nodes = []
        for key in item_keys:
            value = item.get(key)
            if value:
                item_nodes.append(f'<{key}>{escape(value)}</{key}>')
        nodes.append(''.join(item_nodes))
    items_string = ''.join((f'<item>{tmp}</item>' for tmp in nodes))
    return rf'''<?xml version="1.0" encoding="UTF-8" ?>
<rss version="2.0">
<channel>
  <title>{channel_title}</title>
  <link>{channel_link}</link>
  <description>{channel_desc}</description>
  <language>{channel_language}</language>
  {items_string}
</channel>
</rss>
'''
