# xiaohongshu-search-mcp：免登录的小红书搜索 MCP

让 Claude Code、Codex、Cursor、Claude Desktop 这类 AI 工具直接**搜小红书笔记、读全文和评论、查博主、看热点**。
**不用登录小红书，不用 Cookie，不开浏览器**，你自己的小红书账号完全不参与，也就不存在被风控的问题。

一个文件、不装依赖，Python 3.9 以上就能跑。只读，不能发笔记、点赞或私信。

## 30 秒接上

1. 在 [okdata](https://okdata.online/zh/signup/?src=gh-xiaohongshu-search-mcp) 注册拿一个 key（以 `okd_` 开头）。
2. 下载：

```bash
git clone https://github.com/okdataapi/xiaohongshu-search-mcp
cd xiaohongshu-search-mcp
```

3. 加到你的 AI 工具里（把 `okd_...` 换成你的 key，`/完整路径/` 换成上面目录的路径）。

**Claude Code**

```bash
claude mcp add xiaohongshu --scope user -e OKDATA_API_KEY=okd_... -- python3 "$PWD/server.py"
```

**Cursor**（`~/.cursor/mcp.json`）、**Claude Desktop**（`claude_desktop_config.json`）

```json
{
  "mcpServers": {
    "xiaohongshu": {
      "command": "python3",
      "args": ["/完整路径/xiaohongshu-search-mcp/server.py"],
      "env": { "OKDATA_API_KEY": "okd_..." }
    }
  }
}
```

**Codex**（`~/.codex/config.toml`）

```toml
[mcp_servers.xiaohongshu]
command = "python3"
args = ["/完整路径/xiaohongshu-search-mcp/server.py"]
env = { OKDATA_API_KEY = "okd_..." }
```

key 只写在你自己用户目录下的配置里，不要放进项目仓库。

## 能做什么

| 工具 | 作用 | 价格 |
|---|---|---|
| `search_notes` | 按关键词搜笔记，可按综合、最新、最热，可只看视频或图文；一页约 20 条 | $0.02 / 次 |
| `get_note` | 一篇笔记的全文、全部图片、话题和互动数；支持链接、App 分享文字、xhslink 短链 | $0.02 / 次 |
| `note_comments` | 笔记下的评论，带点赞、回复数、IP 属地；一页约 10 条 | $0.02 / 次 |
| `get_user` | 博主的粉丝、获赞与收藏、笔记数和简介 | $0.02 / 次 |
| `user_notes` | 博主最近发的笔记，从新到旧 | $0.02 / 次 |
| `hot_topics` | 小红书当前推荐给创作者的热点话题 | $0.02 / 次 |

调用失败不扣钱。每个结果都带 `cost_usd`（这次花了多少）和抓取时间，AI 可以据此告诉你花了多少钱、数据是什么时候的。
返回的是精简字段，省 token。

可以直接这样问：

- “搜一下小红书上最近关于‘露营 装备’最火的 10 篇笔记，按收藏数排个表。”
- “读一下这篇笔记的评论，总结大家夸什么、吐槽什么：<粘贴分享文字>”
- “这个博主粉丝多少、最近都发什么？<主页链接>”

## 不想跑本地进程？

okdata 有远程 MCP：`https://api.okdata.online/mcp`（Streamable HTTP，请求头 `Authorization: Bearer okd_...`）。
除了小红书，还能查抖音、微信、快手、B站、微博、知乎、TikTok、X、YouTube、Instagram、Reddit 等，共 17 个平台、200 多个接口。配置方法见
[okdata.online/zh/agents.md](https://okdata.online/zh/agents.md)。

## 说明

- 这是 [okdata](https://okdata.online/zh/) 的示例项目，不是小红书的官方项目。`server.py` 只调用 okdata 的接口，本身没有爬虫。
  接口文档：[笔记搜索](https://okdata.online/zh/apis/xiaohongshu/notes/search/)、[笔记详情](https://okdata.online/zh/apis/xiaohongshu/notes/get/)、
  [笔记评论](https://okdata.online/zh/apis/xiaohongshu/notes/comments/list/)。
- 只读取公开内容。请尊重作者版权和用户隐私，不要用来骚扰或批量收集个人信息。
- 测试：`python3 -m unittest discover -s tests`（本地模拟服务器，不联网、不花钱）。
- 问题和建议请提 issue。MIT 许可证。

---

## English

A Xiaohongshu (RedNote) MCP server that needs no login: no account, no cookies, no browser. Six read-only tools
let Claude Code, Codex, Cursor and other MCP clients search notes, read full text and comments, look up creators
and see hot topics, at $0.02 a call (failed calls are free). One Python 3.9+ file, standard library only, stdio
transport. Needs an okdata key in `OKDATA_API_KEY`: [sign up](https://okdata.online/signup/?src=gh-xiaohongshu-search-mcp).

```bash
claude mcp add xiaohongshu --scope user -e OKDATA_API_KEY=okd_... -- python3 /path/to/server.py
```

Prefer a hosted server? Use okdata's remote MCP at `https://api.okdata.online/mcp` (17 platforms, 200+ endpoints).
Unofficial; public data only. MIT licence.
