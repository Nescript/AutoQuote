from gbt7714.models import Author, JournalArticle, WebResource
from gbt7714.formatters import format_reference
from gbt7714.parser import parse_reference

def test_journal_more_than_three():
    a = JournalArticle(
        title='示例标题',
        authors=[
            Author(last='张', first='三'),
            Author(last='李', first='四'),
            Author(last='王', first='五'),
            Author(last='赵', first='六'),
        ],
        journal='测试期刊',
        year=2024,
        volume='10',
        issue='2',
        pages='1-10'
    )
    ref = format_reference(a)
    assert '等' in ref  # 全中文作者超过三人使用 等
    assert '张三, 李四' in ref  # 逗号分隔
    assert ': 1-10' in ref  # 冒号后有空格
    assert ', 2024,' in ref  # 年份部分存在


def test_journal_english_authors_et_al():
    a = JournalArticle(
        title='Intelligent robotics and applications',
        authors=[
            Author(last='Yu', first='Hongbo'),
            Author(last='Liu', first='Jinguo'),
            Author(last='Liu', first='Liqiang'),
            Author(last='Wang', first='Wei'),
        ],
        journal='Example Journal',
        year=2023,
        volume='12',
        issue='1',
        pages='20-30'
    )
    ref = format_reference(a)
    assert 'et al.' in ref
    assert 'Yu H' in ref or 'Yu H B' in ref


def test_web_resource():
    w = WebResource(
        title='Robots',
        authors=[Author(last='INNFOS', is_organization=True)],
        url='https://innfos.com/',
    )
    ref = format_reference(w)
    assert '[EB/OL]' in ref
    assert ref.endswith('https://innfos.com/.')


def test_normalize_journal():
    raw = 'Yu H B, Liu J G, Liu L Q, et al. Intelligent robotics and applications[J]. Example Journal, 2023, 12(1): 20-30. DOI: 10.1000/xyz123'
    entry = parse_reference(raw)
    formatted = format_reference(entry)
    assert 'Intelligent robotics and applications[J]' in formatted
    assert 'DOI: 10.1000/xyz123' in formatted


def test_normalize_web():
    raw = 'INNFOS. Robots[EB/OL]. (2020-01-01) [2020-04-30]. https://innfos.com/'
    entry = parse_reference(raw)
    formatted = format_reference(entry)
    assert formatted.startswith('INNFOS. Robots[EB/OL]')
    assert formatted.endswith('https://innfos.com/.')


def test_apa_conference():
    raw = 'Vaswani, A., Shazeer, N.M., Parmar, N., Uszkoreit, J., Jones, L., Gomez, A.N., Kaiser, L., & Polosukhin, I. (2017). Attention is All you Need. Neural Information Processing Systems.'
    entry = parse_reference(raw)
    formatted = format_reference(entry)
    assert '[C]' in formatted  # 会议输出标识
    assert 'Attention is All you Need[C]' in formatted


def test_apa_journal():
    raw = 'Smith, J., Doe, A. B., & Zhang, W. (2021). A novel method for something. Journal of Interesting Results, 15(2), 123-135. https://doi.org/10.1234/abc.def/5678'
    entry = parse_reference(raw)
    formatted = format_reference(entry)
    assert '[J]' in formatted
    assert 'Journal of Interesting Results' in formatted
    assert '123-135' in formatted
    assert '10.1234/abc.def/5678' in formatted

def test_bibtex_inproceedings():
    raw = '''@inproceedings{Vaswani2017AttentionIA,
    title={Attention is All you Need},
    author={Ashish Vaswani and Noam M. Shazeer and Niki Parmar and Jakob Uszkoreit and Llion Jones and Aidan N. Gomez and Lukasz Kaiser and Illia Polosukhin},
    booktitle={Neural Information Processing Systems},
    year={2017},
    url={https://api.semanticscholar.org/CorpusID:13756489}
}'''
    entry = parse_reference(raw)
    formatted = format_reference(entry)
    assert '[C]' in formatted
    assert 'Attention is All you Need[C]' in formatted
    assert 'Neural Information Processing Systems' in formatted

def test_legacy_nips_style():
    raw = 'Vaswani, Ashish, et al. "Attention is all you need." Advances in neural information processing systems 30 (2017).'
    entry = parse_reference(raw)
    formatted = format_reference(entry)
    assert '[J]' in formatted
    assert 'Advances in neural information processing systems' in formatted
    assert '2017, 30' in formatted or '2017, 30(' in formatted

if __name__ == '__main__':
    test_journal_more_than_three()
    test_journal_english_authors_et_al()
    test_web_resource()
    test_normalize_journal()
    test_normalize_web()
    test_apa_conference()
    test_apa_journal()
    test_bibtex_inproceedings()
    test_legacy_nips_style()
    print('All tests passed.')
