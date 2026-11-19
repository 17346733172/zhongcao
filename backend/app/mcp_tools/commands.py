"""Recognize explicit creation quantities independently of semantic tool selection."""

import re
import unicodedata

# Prescription words denote execution only when qualified as test/simulation data.
# These conservative rules authorize writes only; they do not route read queries.
EXECUTION_SUBJECT = (
    r'(?:(?:匿名|仿真|模拟|演示|测试)*(?:任务|作业|批次)'
    r'|(?:匿名|仿真|模拟|演示|测试)*(?:仿真|模拟|演示|测试)(?:方子|处方|药方))'
)
CREATION = re.compile(
    r'(?:下发|下达|安排|创建|新建|生成|下)'
    r'([0-9]+|[零〇一二两三四五六七八九十百]+)'
    rf'(?:个|项|条|批|份|张|副){EXECUTION_SUBJECT}'
)
CHINESE_DIGITS = {c: i for i, c in enumerate('零一二三四五六七八九')}
CHINESE_DIGITS['两'] = 2


def normalize_command(question):
    return re.sub(r'\s+', '', unicodedata.normalize('NFKC', question))


def requested_creation_count(question):
    matches = CREATION.findall(normalize_command(question))
    if len(matches) != 1:
        return None
    number = matches[0]
    if number.isascii() and number.isdigit():
        return int(number)
    if number in CHINESE_DIGITS:
        return CHINESE_DIGITS[number]
    if re.fullmatch(r'[一二三四五六七八九]?十[一二三四五六七八九]?', number):
        tens, units = number.split('十')
        return CHINESE_DIGITS.get(tens, 1) * 10 + CHINESE_DIGITS.get(units, 0)
    return None
