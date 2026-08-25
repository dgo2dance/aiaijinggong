# 艾艾精工形态相似选股器

每日收盘后自动扫描全A股，找出与艾艾精工 (603580) 走势形态相似的标的。

## 功能

- 自动检测艾艾精工启动日，构建蓄势段+拉升段双模板
- 并发扫描全A股（新浪+腾讯+akshare），DTW+相关+量能多维匹配
- 生成可视化 HTML 报告（走势叠加对比图 + 明细表）
- GitHub Actions 每日16:00自动运行，报告发布到 GitHub Pages
- 微信 PushPlus 推送 Top 10 命中标的

## 报告查看

访问地址：**https://dgo2dance.github.io/aiaijinggong/**

## 手动运行

```bash
pip install -r requirements.txt

# 全A扫描（含微信推送）
python3 -m src.scanner --push

# 全A扫描（不含推送）
python3 -m src.scanner

# 快速演示（7只票）
python3 -m src.scanner --pool csv --limit 7

# 生成报告
python3 -m src.report outputs/aiai_pattern_scan_xxx.csv docs/report.html
```

## GitHub Pages 配置

1. 打开仓库 Settings → Pages
2. Source 选择 `master` 分支
3. Folder 选择 `/docs`
4. 点击 Save
5. 等待 1-2 分钟后访问：https://dgo2dance.github.io/aiaijinggong/

## GitHub Actions 配置

Settings → Secrets and variables → Actions 中添加 Secret：
- `PUSHPLUS_TOKEN`：PushPlus 用户 Token（从 [pushplus.plus](https://www.pushplus.plus) 获取）

## 分类说明

| 分类 | 条件 |
|------|------|
| 刚启动(拉升初期) | 拉升段相似度≥55 且 形状≥0.35 且近5日回撤≤12% |
| 启动前(蓄势中) | 蓄势段相似度≥55 且 形状≥0.35 |
| 形态接近(观察) | 综合相似度≥48 |

## 依赖

- Python 3.9+
- pandas / numpy / requests / akshare
