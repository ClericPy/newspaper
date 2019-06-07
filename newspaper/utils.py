import aiofiles


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
