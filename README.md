# AutoQuote

面向 GB/T 7714-2015（顺序编码制）参考文献条目的解析与格式化工具。支持从多种常见输入（GB/T 片段、APA、BibTeX、简单网页条目）生成规范化引用及 LaTeX `\bibitem`。

## 主要功能

| 范畴 | 内容 |
|------|------|
| 支持类型 | 期刊 `[J]`, 会议 `[C]`, 图书 `[M]`, 网页 `[EB/OL]` |
| 解析格式 | GB/T 行文、APA 期刊/会议、BibTeX (`@article/@inproceedings/@book/@misc`)、含日期的网页条目 |
| 作者处理 | 中英文混合；>3 自动“等”/`et al.`；机构作者识别；中文姓名连续输入拆分 |
| 标准化 | DOI 前缀裁剪；URL 保留；页码/卷(期)提取 |
| LaTeX 输出 | 自动生成 `\bibitem{key}`（可编辑），按首作者+年份生成缺省键 |
| GUI | 粘贴→解析→GB/T→bibitem 一体；另供字段手工录入 |

## 安装

要求 Python ≥ 3.9。

```powershell
python -m venv .venv
. .venv/Scripts/Activate.ps1
pip install -r requirements.txt
```

## 使用

命令行示例：
```powershell
python main.py demo
python main.py normalize "INNFOS. Robots[EB/OL]. (2020-01-01) [2020-04-30]. https://innfos.com/"
```

启动 GUI：
```powershell
python gui.py
```

## GUI 简述

解析/标准化 (主)：粘贴任意支持格式 → 输出 GB/T 规范串 + bibitem。

字段录入 (辅)：逐字段填写；作者框支持中文连续姓名、顿号/逗号/分号/换行混合分隔。

## 示例

APA 期刊输入：
```
Smith, J., Doe, A. B., & Zhang, W. (2021). A novel method for something. Journal of Interesting Results, 15(2), 123-135. https://doi.org/10.1234/abc.def/5678
```
GB/T 输出：
```
Smith J, Doe A B, Zhang W. A novel method for something[J]. Journal of Interesting Results, 2021, 15(2): 123-135. DOI: 10.1234/abc.def/5678
```

BibTeX `@inproceedings` 输入：
```
@inproceedings{Vaswani2017AttentionIA,
  title={Attention is All you Need},
  author={Ashish Vaswani and Noam M. Shazeer and Niki Parmar and Jakob Uszkoreit and Llion Jones and Aidan N. Gomez and Lukasz Kaiser and Illia Polosukhin},
  booktitle={Neural Information Processing Systems},
  year={2017},
  url={https://api.semanticscholar.org/CorpusID:13756489}
}
```
部分作者截断后输出：
```
Vaswani A, Shazeer N M, Parmar N, et al. Attention is All you Need[C] // Neural Information Processing Systems. 2017.
```

网页条目：
```
大洋网. 目的地15公里以内，旅客飞抵白云机场可选乘“短途专车”[EB/OL]. (2024-02-07) [2025-07-23]. https://news.dayoo.com/guangzhou/202402/07/139995_54628954.htm
```

## 目录结构
```
gbt7714/
  models.py        # 数据模型
  formatters.py    # 格式化实现
  parser.py        # 解析 (GB/T / APA / BibTeX / Web)
gui.py             # GUI
main.py            # CLI
tests.py           # 测试
```

## 测试
```powershell
python tests.py
```

## 规划（简）

| 功能 | 状态 |
|------|------|
| BibTeX 基础类型 | 已实现 |
| APA 解析 | 已实现 |
| 学位论文 / 报告类型 | 规划 |
| 批量多条解析 | 规划 |
| .bib / RIS 导出 | 规划 |
| 外部元数据接口 | 规划 |

## 贡献

1. Fork 仓库并建分支
2. 修改或新增代码与测试
3. 确保 `tests.py` 全部通过后提交 PR

## 许可证

MIT
