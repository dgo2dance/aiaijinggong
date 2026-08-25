# 艾艾精工形态相似选股器

每日收盘后自动扫描全A股，找出与艾艾精工 (603580) 走势形态相似的标的。

## 功能

- 自动检测艾艾精工启动日，构建蓄势段+拉升段双模板
- 并发扫描全A股（新浪行情），DTW+相关+量能多维匹配
- 生成可视化 HTML 报告（走势叠加对比图 + 明细表）
- GitHub Actions 每日16:00自动运行，报告发布到 GitHub Pages
- 微信 PushPlus 推送 Top 10 命中标的

## 报告查看

访问地址：**https://dgo2dance.github.io/zhushenglang/**

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

## GitHub Actions 配置

1. 推送到 GitHub 仓库
2. Settings → Pages → Source 选择 `master` 分支 `/docs` 目录
3. Settings → Secrets and variables → Actions 中添加 Secret：
   - `PUSHPLUS_TOKEN`：PushPlus 用户 Token（从 [pushplus.plus](https://www.pushplus.plus) 获取）
4. 工作流会自动运行，也可在 Actions 页面手动触发

## 分类说明

| 分类 | 条件 |
|------|------|
| 刚启动(拉升初期) | 拉升段相似度≥55 且 形状≥0.35 且近5日回撤≤12% |
| 启动前(蓄势中) | 蓄势段相似度≥55 且 形状≥0.35 |
| 形态接近(观察) | 综合相似度≥48 |

## 依赖

- Python 3.9+
- pandas / numpy / requests
