"""Resolve bundled Jieba configs to filesystem paths for opencc-py 1.4.2."""

from opencc import OpenCC as _OpenCC
from opencc_data import config_path


def OpenCC(config):
    if isinstance(config, str) and '_jieba' in config and '/' not in config:
        name = config if config.endswith('.json') else f'{config}.json'
        # The pure Python backend needs config_dir to resolve Jieba resources.
        return _OpenCC(str(config_path(name)))
    return _OpenCC(config)
