from __future__ import annotations
from gbt7714.models import Author, JournalArticle, Book, WebResource
from gbt7714.formatters import format_reference
from gbt7714.parser import parse_reference
from datetime import date
import argparse


def demo():
    examples = []
    examples.append(JournalArticle(
        title='深度学习在医学图像分析中的应用',
        authors=[Author(last='张', first='三'), Author(last='李', first='四'), Author(last='Wang', first='Li'), Author(last='赵', first='六')],
        journal='计算机科学',
        year=2024,
        volume='50',
        issue='2',
        pages='12-20',
        doi='10.1234/abc.2024.001'
    ))
    examples.append(Book(
        title='Python 编程实践',
        authors=[Author(last='刘', first='伟')],
        publisher='机械工业出版社',
        place='北京',
        year=2023,
        edition='2'
    ))
    examples.append(WebResource(
        title='GB/T 7714-2015 标准简介',
        authors=[Author(last='国家标准化管理委员会', is_organization=True)],
        url='https://www.example.com/gbt7714',
        date_accessed=date.today(),
        date_published=date(2015, 12, 1)
    ))

    for i, e in enumerate(examples, start=1):
        print(f"[{i}] {format_reference(e)}")


def main():
    parser = argparse.ArgumentParser(description='GB/T 7714-2015 引用格式工具')
    parser.add_argument('command', nargs='?', default='demo', help='命令: demo | normalize')
    parser.add_argument('-t', '--text', help='需要标准化的原始参考文献字符串（需包含类型标识如 [J]）')
    args = parser.parse_args()
    if args.command == 'demo':
        demo()
    elif args.command == 'normalize':
        if not args.text:
            print('请使用 -t 传入原始参考文献字符串')
            return
        try:
            entry = parse_reference(args.text)
            print(format_reference(entry))
        except Exception as e:
            print(f'解析失败: {e}')
    else:
        print('未知命令')

if __name__ == '__main__':
    main()
