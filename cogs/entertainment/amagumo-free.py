import asyncio
import json
from datetime import date
from json import load
from time import time
from typing import Callable

import aiohttp
import discord
from discord.ext import commands, tasks

TMU = Callable[[str, int], str]
global options,area
options = []
area = []
BASE_URL = "https://img.weather.goo.ne.jp/images/mesh/"
    # 時間誤差指定、内包表記でやった方がコード短くなるから内包表記にした。
ERROR_TIME = {i: f"_{i}.png?" for i in range(6)}

doreka = "どれか選択してください"

zen = {
    "北海道":doreka,
    "全国":doreka,
    "東北":doreka,
    "関東":doreka,
    "中部":doreka,
    "近畿":doreka,
    "中国":doreka,
    "四国":doreka,
    "九州":doreka
}
for k,v in zen.items():
    options.append(discord.SelectOption(label=k,description=v))

def make_url(place: str, error_time: int) -> str:
        # 雨雲レーダーの画像のURLを作る。
        # https://img.weather.goo.ne.jp/images/mesh/p0008_0.png?202109101218
        # のようなものを作る。この時`mesh/`まではBASE_URLにある。その他は辞書にある。
        # 一番最後の`?cache_killer=`は無駄のように見えるがこれがないとキャッシュのせいで一日立たないと画像が更新されない。
    return (
        f"{BASE_URL}{PREFECTURES[place]}{ERROR_TIME[error_time]}"
        "{0::%Y%m%d}".format(date.today()) + f"?cache_killer={time()}"
    )

class Dropdown_tihou(discord.ui.Select):
    #ドロップダウンのclass
    def __init__(self):
        super().__init__(placeholder='地方を選択してください', min_values=1, max_values=1, options=options,disabled=False)
    async def callback(self, interaction: discord.Interaction):
        url = make_url(self.values[0], 0)
        embed = discord.Embed(color=0x2ecc71,title=f"{self.values[0]} 雨雲レーダー")
        embed.set_image(url=url)
        await interaction.response.edit_message(embed=embed,view=AmagumoView(make_url, 0))



class DropdownView(discord.ui.View):
    def __init__(self):
        super().__init__()

        # Adds the dropdown to our view object.
        self.add_item(Dropdown_tihou())


class AmagumoView(discord.ui.View):
    # 雨雲レーダーのメニューのView
    def __init__(self, make_url: TMU, page: int):
        self.make_url: TMU = make_url
        self.page: int = page
        super().__init__()
    async def switching(self, interaction, button, mode):
        # ページを切り替える際に呼び出される関数です。
        # 今表示しているページ数が何時間後の雨雲レーダー画像かどうかとなっている。
        if mode == "left":
            self.page = (self.page + 5) % 6
        elif mode == "right":
            self.page = (self.page + 1) % 6

        # 元のメッセージのEmbedを取り出す。
        embed = interaction.message.embeds[0]
        # 元のメッセージのEmbedの画像を変更する。その際に新しい雨雲レーダー画像のURLを取得する。
        # この時`make_url`を使うがこれに渡す引数placeで`embed.title.split()[0]`にしている。
        # これはEmbedのタイトルから雨雲レーダー画像の地域の名前を取り出している。
        embed.set_image(url=self.make_url(embed.title.split()[0], self.page))

        await interaction.response.edit_message(embed=embed)

    @discord.ui.button(emoji="⏪")
    async def left(self, button, interaction):
        await self.switching(button, interaction, "left")

    @discord.ui.button(emoji="⏩")
    async def right(self, button, interaction):
        await self.switching(button, interaction, "right")

PREFECTURES = {
    "全国": "zenkoku",
    "北海道": "r001",
    "東北": "r002",
    "関東": "r003",
    "中部": "r004",
    "近畿": "r005",
    "中国": "r006",
    "九州": "r007",
}
class amagumoCog(commands.Cog):

    # ベースURL
    BASE_URL = "https://img.weather.goo.ne.jp/images/mesh/"
    # 時間誤差指定、内包表記でやった方がコード短くなるから内包表記にした。
    ERROR_TIME = {i: f"_{i}.png?" for i in range(6)}


    @commands.command(aliases=["天気", "雨雲"])
    @commands.cooldown(1, 7, commands.BucketType.user)
    async def tenki(self, ctx):
        global area
        area = []
        embed = discord.Embed(color=0x2ecc71,title=f"雨雲レーダー",description="地方を選択してください。")
        await ctx.reply(embed=embed, view=DropdownView())

async def setup(bot):
    await bot.add_cog(amagumoCog(bot))
    print("[SystemLog] 雨雲 Cog：ロード完了")
