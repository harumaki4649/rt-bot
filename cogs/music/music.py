# RT Music - Music Data class

from typing import (
    TYPE_CHECKING, TypedDict, Type, Callable, Literal, Union, Optional, Any
)

from time import time

import discord
from jishaku.functools import executor_function

from niconico import NicoNico, objects as niconico_objects
from youtube_dl import YoutubeDL

if __name__ == "__main__":
    from .__init__ import MusicCog


#   youtube_dl用のオプションの辞書
# 音楽再生時に使用するオプション
NORMAL_OPTIONS = {
    "format": "bestaudio/best",
    "default_search": "auto",
    "logtostderr": False,
    "cachedir": False,
    "ignoreerrors": True,
    "source_address": "0.0.0.0",
    "cookiefile": "data/youtube-cookies.txt"
}
# 音楽情報取得に使うオプション
FLAT_OPTIONS = {
    "extract_flat": True,
    "source_address": "0.0.0.0",
    "cookiefile": "data/youtube-cookies.txt"
}


#   型等
class MusicTypes:
    "何のサービスの音楽かです。"

    niconico = 1
    youtube = 2
    soundcloud = 3


class MusicDict(TypedDict):
    "プレイリスト等に保存する際の音楽データの辞書の型です。"

    music_type: int
    title: str
    url: str
    thumbnail: str
    duration: Optional[int]
    extras: Any


#   Utils
niconico = NicoNico()
def make_niconico_music(
    cog: MusicCog, author: discord.Member, url: str, video: Union[
        niconico_objects.Video, niconico_objects.MyListItemVideo
    ]
) -> Music:
    "ニコニコ動画のMusicクラスのインスタンスを用意する関数です。ただのエイリアス"
    return Music(
        cog, author, MusicTypes.niconico, video.title, url,
        video.thumbnail.url, video.duration
    )


def get_music_by_ytdl(url: str, mode: Literal["normal", "flat"]) -> dict:
    "YouTubeのデータを取得する関数です。ただのエイリアス"
    return YoutubeDL(globals()[mode.upper()]).extract_info(url, download=False)


def make_youtube_url(data: dict) -> str:
    "渡された動画データからYouTubeの動画URLを作ります。"
    return f"""https://www.youtube.com/watch?v={
        data.get("display_id", data.get("id", "3JW1qw7HB5U"))
    }"""


def format_time(time_: Union[int, float]) -> str:
    "経過した時間を`01:39`のような`分：秒数`の形にフォーマットする。"
    return ":".join(
        map(lambda o: (
            str(int(o[1])).zfill(2)
            if o[0] or o[1] <= 60
            else format_time(o[1])
        ), ((0, time_ // 60), (1, time_ % 60)))
    )


#   メインディッシュ
class Music:
    "音楽のデータを格納するためのクラスです。"

    on_close: Callable[..., Any] = lambda : None
    """音楽再生終了後に呼び出すべき関数です。
    ニコニコ動画の音楽を再生した場合は再生終了後にこれを呼び出してください。"""

    def __init__(
        self, cog: MusicCog, author: discord.Member, music_type: int, title: str,
        url: str, thumbnail: str, duration: Union[int, None], extras: Any = {}
    ):
        self.extras, self.title, self.url = extras, title, url
        self.thumbnail, self.duration = thumbnail, duration
        self.music_type, self.cog, self.author = music_type, cog, author

        self._start = 0.0

    def to_dict(self) -> MusicDict:
        "このクラスに格納されているデータをJSONにシリアライズ可能な辞書にします。"
        return MusicDict(
            music_type=self.music_type, title=self.title, url=self.url,
            thumbnail=self.thumbnail, duration=self.duration, extras=self.extras
        )

    @classmethod
    def from_dict(cls, cog: MusicCog, author: discord.Member, data: MusicDict) -> Music:
        "MusicDictに準拠した辞書からMusicクラスのインスタンスを作成します。"
        return cls(cog, author, **data)

    @classmethod
    @executor_function
    def from_url(
        cls, cog: MusicCog, author: discord.Member, url: str, max_result: int
    ) -> Union[Music, tuple[list[Music], bool], Exception]:
        """音楽を取得します。
        ニコニコ動画のマイリストやYouTubeの再生リストを渡した場合はそのリストと最大取得数でカンストしたかどうかのタプルが返されます。
        取得に失敗した場合はエラーが返されます。"""
        try:
            if "nicovideo.jp" in url or "nico.ms" in url:
                # ニコニコ動画
                if "mylist" in url:
                    # マイリストの場合
                    items, length, count_stop = [], 0, True
                    for mylist in niconico.video.get_mylist(url):
                        length += len(mylist.items)
                        items.extend([
                            make_niconico_music(
                                cog, author, item.video.url, item.video
                            )
                            for item in mylist.items
                        ])
                        if length > max_result:
                            items = items[:max_result]
                            break
                    else:
                        count_stop = False
                    return items, count_stop
                # マイリストではなく通常の動画の場合
                video = niconico.video.get_video(url)
                return make_niconico_music(cog, author, video.url, video.video)
            elif "soundcloud.com" in url or "soundcloud.app.goo.gl" in url:
                if "goo" in url:
                    # 短縮URLの場合はリダイレクト先が本当の音楽のURLなのでその真のURLを取得する。
                    async with cog.client_session.get(url) as r:
                        url = str(r.url)
                data = get_music_by_ytdl(url, "flat")
                return cls(
                    cog, author, MusicTypes.soundcloud, data["title"], url,
                    data["thumbnail"], data["duration"]
                )
            else:
                # YouTube
                if not url.startswith(("http://", "https://")):
                    # 検索の場合はyoutube_dlで検索をするためにytsearchを入れる。
                    url = f"ytsearch15:{url}"

                data = get_music_by_ytdl(url, "flat")
                if data["entries"]:
                    # 再生リストなら
                    items = []
                    for count, entry in enumerate(data["entries"], 0):
                        if count == max_result:
                            return items, True
                        items.append(
                            cls(
                                cog, author, MusicTypes.youtube, entry["title"],
                                make_youtube_url(entry),
                                f"http://i3.ytimg.com/vi/{entry['id']}/hqdefault.jpg",
                                entry["duration"]
                            )
                        )
                    else:
                        return items, False
                # 通常の動画なら
                return cls(
                    cog, author, MusicTypes.youtube, data["title"],
                    make_youtube_url(data), data["thumbnail"], data["duration"]
                )
        except Exception as e:
            cog.print("Failed to load music: %s: %s" % (e, url))
            return e

    @executor_function
    def _prepare_source(self) -> str:
        "音楽再生に使う動画の直URLの準備をします。"
        if self.music_type == (MusicTypes.youtube, MusicTypes.soundcloud):
            return get_music_by_ytdl(self.url, "normal")["url"]
        elif self.music_type == MusicTypes.niconico:
            self.video = niconico.video.get_video(self.url)
            self.video.connect()
            setattr(self, "on_close", self.video.close)
            return self.video.download_link
        assert False, "あり得ないことが発生しました。"

    async def make_source(self) -> Union[
        discord.PCMVolumeTransformer, discord.FFmpegOpusAudio
    ]:
        "音楽再生のソースのインスタンスを作ります。"
        if discord.opus.is_loaded():
            # 通常
            return discord.PCMVolumeTransformer(
                discord.FFmpegPCMAudio(await self._prepare_source())
            )
        else:
            # もしOpusライブラリが読み込まれていないのならFFmpegにOpusの処理をしてもらう。
            # その代わり音量調整はできなくなる。(本番環境ではここは実行されないのでヨシ！)
            return discord.FFmpegOpusAudio(
                await self._prepare_source()
            )

    def start(self) -> None:
        "途中経過の計算用の時間を計測を開始する関数です。"
        self._start = time()

    def toggle_pause(self):
        "途中経過の時間の計測を停止させます。また、停止後に実行した場合は計測を再開します。"
        if self._stop == 0.0:
            self._stop = time()
        else:
            self._start += self.stop
            self._stop = 0.0

    @executor_function
    def stop(self, callback: Callable[..., Any]) -> None:
        "音楽再生終了時に実行すべき関数です。"
        self.on_close()
        callback()

    @property
    def maked_title(self) -> str:
        "マークダウンによるURLリンク済みのタイトルの文字列を返します。"
        return f"[{self.title}]({self.url})"

    @property
    def now(self) -> float:
        "何秒再生してから経過したかです。"
        return time() - self._start

    @property
    def formated_now(self) -> str:
        "フォーマット済みの経過時間です。"
        return format_time(self.now)

    @property
    def elapsed(self) -> str:
        "何秒経過したかの文字列です。`/`"
        return f"{self.formated_now}/{self.duration or '??:??'}"

    def make_seek_bar(self, length: int = 15) -> str:
        "どれだけ音楽が再生されたかの絵文字によるシークバーを作る関数です。"
        if self.duration is None:
            return ""
        return "".join((
            (base := "◾" * length
            )[:(now := int(self.now / self.duration * length))],
            "⬜", base[now:])
        )

    def __str__(self):
        return f"<Music title={self.title} elapsed={self.elapsed} author={self.author} url={self.url}>"