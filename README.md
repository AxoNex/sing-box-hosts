# sing-box-hosts

定时从 `rules.json` 中配置的 hosts 源自动抓取广告屏蔽规则，并转换成各平台的规则文件，输出到 `rules/block/`。

## 工作原理

- `rules.json` 的 `block` 字段：每个 key 是一条规则名，value 是该规则对应的 hosts 文件 URL。
- `rules.json` 的 `platforms` 字段：需要转换成的平台（服务类型）。
- GitHub Actions 每 24 小时（每天 00:00 UTC）运行一次 `generate.py`，抓取 hosts → 解析域名 → 生成规则文件并提交推送。

## 输出命名

`rules/block/<规则名>-<服务类型>.<扩展名>`，例如规则 `秋风广告规则` 会生成：

- `rules/block/秋风广告规则-singbox.json`（sing-box rule-set 源格式：`{"version":3,"rules":[{"domain":[...]}]}`）
- `rules/block/秋风广告规则-hosts.txt`（每行 `0.0.0.0 <域名>`）

## 平台类型

| platforms 值 | 输出文件 | 格式 |
| --- | --- | --- |
| `sing-box` | `<规则名>-singbox.json` | sing-box rule-set 源格式 `{"version":3,"rules":[{"domain":[...]}]}` |
| `hosts` | `<规则名>-hosts.txt` | 每行 `0.0.0.0 <域名>` |

新增平台时，只需在 `generate.py` 的 `PLATFORM_OUTPUT` 和 `CONVERTERS` 中补充对应映射与转换函数。

## 本地运行

```bash
python generate.py
```
