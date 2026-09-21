# selene-iptv

给 Selene-TV 使用的 CCTV + 省级卫视直播订阅生成器。

## 直接使用

Selene-TV 的订阅地址：

```
https://raw.githubusercontent.com/daoshengtianxia123/selene-iptv/main/selene-sub.txt
```

生成文件：

- `live.m3u`：央视 + 卫视
- `cctv.m3u`：央视
- `province.m3u`：卫视
- `selene-sub.txt`：符合 Selene-TV 订阅规范的 Base58 文本

## 工作方式

GitHub Actions 每 6 小时运行一次 `scripts/update.py`。脚本从多个公开上游 M3U/M3U8 列表读取候选频道，统一 CCTV/卫视频道名称、去重，并按上游优先级与可用的响应时间信息选择一个候选 URL。

当前上游：

- best-fan/iptv-sources：CCTV、卫视主来源
- zilong7728/Collect-IPTV：备用来源
- vbskycn/iptv：备用来源

本仓库不保存或转发任何视频内容，只生成播放列表。上游地址可能失效、受地区/运营商限制或具有各自的授权条件；使用前请确认你有权访问对应内容。

## 手动更新

```bash
python3 scripts/update.py
```

也可以在 GitHub 仓库的 **Actions → Update IPTV → Run workflow** 手动运行一次。
