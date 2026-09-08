# 邪神战记 词表在线仓库（JashinsenkiNameTranslation 分发源）

本仓库用于向插件 `JashinsenkiNameTranslation`（v1.4.0 起）分发**角色名与角色档案词表**。
插件启动时按 `RemoteBaseUrl` 拉取 `zh-CN/manifest.json` → 比对/下载 `zh-CN/pack.json`（SHA-256 校验）→ 原子拆包写盘生效。

## 目录布局（提交到仓库根）

```
<repo>/
  README.md
  zh-CN/
    manifest.json      ← 清单（schemaVersion/language/packFile/packSha256/counts）
    pack.json          ← 词表包（names + profiles 两个词表对象）
```

- 每次词表有更新：重跑 `jashinsenki-cn\tools\build-release.ps1`（生成两个文件）→ 提交推送即可；
- 插件无需改版本号——manifest 的 `packSha256` 变化即触发更新。

## 建仓推送步骤（一次性）

```bash
# 1) GitHub 新建一个仓库（公开仓库才能用 raw 直链；若私有请用下方 jsdelivr/ghproxy 方案或公开）
# 2) 本地
git init <repo>
cd <repo>
# 把 release 目录内容拷进来（README.md、zh-CN/）
git add .
git commit -m "词表初始发布（names 578 / profiles 320）"
git branch -M main
git remote add origin https://github.com/<你的用户名>/<仓库名>.git
git push -u origin main
```

## 玩家/使用端配置（BepInEx\config\local.jitsu.jashinsenki.names.cfg）

```ini
[Updates]
# 例：公开仓库 raw 直链（main 分支）
RemoteBaseUrl = https://raw.githubusercontent.com/<你的用户名>/<仓库名>/main

# 或 CDN 镜像（国内更稳，可选）
# RemoteBaseUrl = https://cdn.jsdelivr.net/gh/<你的用户名>/<仓库名>@main
```

- `RemoteBaseUrl` 留空 = 纯本地（等同旧版行为）；`PreferLocalFiles = true` = 永不联网。
- 本地缺词表时首启会自动拉取；之后 `UpdateOnStartup` 启动检查更新。

## 本地自测（无需 GitHub）

把 `release\zh-CN` 通过任意静态服务器发布，例如：
```bash
python -m http.server 8123 -d F:\DeepSeek\邪神汉化\jashinsenki-cn\release
```
cfg `RemoteBaseUrl = http://127.0.0.1:8123` → 启动游戏观察日志：
- 本地词表被清空时自动拉取并“词表已加载”；
- 重新生成 pack 后重启会自动更新（日志记录 packSha256）。

## 内容来源

词表由 `F:\DeepSeek\邪神汉化\jashinsenki-cn` 工程管理（抓包→翻译→校对→`data\zh-CN\*.json`），
构建发布产物命令：`tools\build-release.ps1`。勿手工改本仓库内 pack。
