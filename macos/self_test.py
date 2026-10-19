"""Small runtime check for the installed app and its bundled OpenCC data."""

from mac_opencc import OpenCC


def run_self_test():
    cases = {
        't2gov': ('啟淨', '啓净'),
        't2s': ('繁體中文', '繁体中文'),
        's2t': ('简体中文', '簡體中文'),
        't2gov_jieba': ('啟淨', '啓净'),
        't2gov_jieba_traditional': ('啟淨', '啓净'),
    }
    for mode, (source, expected) in cases.items():
        actual = OpenCC(mode).convert(source)
        if actual != expected:
            raise AssertionError(f'{mode}: {source!r} -> {actual!r}; expected {expected!r}')
        print(f'{mode}: {actual}')
    print('OpenCC resources: OK')


if __name__ == '__main__':
    run_self_test()
