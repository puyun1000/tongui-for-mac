"""Verify the ambiguity engine against the bundled OpenCC conversion rules."""

from text_tab import _load_config, _is_cjk, _get_opencc, convert_with_ambiguities


def main():
    checks = 0
    for config in (
        "t2gov", "t2new", "t2gov_keep_simp", "t2new_keep_simp",
        "t2s", "v2s", "s2t",
    ):
        parsed = _load_config(config)
        ambiguous_keys = [
            key
            for group in parsed.groups
            for dictionary in group.dicts
            for key, values in dictionary.values.items()
            if len(values) > 1 and 1 <= len(key) <= 3 and all(_is_cjk(char) for char in key)
        ]
        sample = f"今日，{ambiguous_keys[0]}，完畢。" if ambiguous_keys else "繁體中文，簡體字。"
        result = convert_with_ambiguities(sample, config)
        expected = _get_opencc(config).convert(sample)
        assert result["output"] == expected, f"{config}: output differs from OpenCC"
        if ambiguous_keys:
            assert result["spans"], f"{config}: expected an ambiguity span"
        for span in result["spans"]:
            converted = result["output"][span["start"]:span["start"] + span["length"]]
            assert converted in span["candidates"], f"{config}: invalid candidate span"
            checks += 1
        print(f"{config}: output matches OpenCC; {len(result['spans'])} ambiguity span(s)")
    print(f"Ambiguity verification passed: {checks} span(s)")


if __name__ == "__main__":
    main()
