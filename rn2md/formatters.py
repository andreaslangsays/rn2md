"""Helpers to transform data in RedNotebook-syntax to Markdown-syntax.

Here is a summary of the currently implemented formatters:

    RedNotebook                       Markdown
    ===========                       ========
    [name ""url""]                    [name](url)
    //text//                          _text_
    --text--                          ~text~
    =Text=                            # Text
    [""url""]                         ![...](url)
    + Ordered item                    1. Ordered item
    - Unordered item                  - Unordered item
    ``asdf``                          `asdf`
"""
import re

import defaultlist

from . import util


@util.prime_coroutine_generator
def format_rednotebook_as_markdown(header_padding=0):
    """Sequences all other formatters to create markdown-formatted lines."""
    ordered_formatters = [
        format_inner_underscores(),
        format_links(),
        format_images(),
        format_headers(padding=header_padding),
        format_code_blocks(),
        format_italic_text(),
        format_strikethrough_text(),
        format_lists(),
    ]
    line = ''
    while True:
        line = yield line
        for formatter in ordered_formatters:
            line = formatter.send(line)


@util.prime_coroutine_generator
def format_links():
    """Transforms '[[text ""url""]]' to '[text](url)'."""
    line = ''
    while True:
        line = yield re.sub(r'\[([^\]]*?) ""(.*?)""\]', r'[\1](\2)', line)


@util.prime_coroutine_generator
def format_images():
    """Transforms '[[""image url""]]' to '![](image url)'."""
    line = ''
    while True:
        line = yield re.sub(r'\[""(.*?)""\]', r'![](\1)', line)


@util.prime_coroutine_generator
def format_italic_text():
    """Transforms '//text//' to '_text_'."""
    line = ''
    while True:
        line = yield _sub_balanced_delims('//', '_', line)


@util.prime_coroutine_generator
def format_strikethrough_text():
    """Transforms '--text--' to '**OBSOLETE**(text)'."""
    line = ''
    while True:
        line = yield line
        if line != ('-' * len(line)):
            line = _sub_balanced_delims('--', '~', line)


@util.prime_coroutine_generator
def format_code_blocks():
    """Transforms codeblocks into markdown-syntax."""
    line = ''
    while True:
        line = yield _sub_balanced_delims('``', '`', line, preds=[_not_in_link])


@util.prime_coroutine_generator
def format_headers(padding=0):
    """Transforms '=TEXT=' into '# TEXT'."""
    line = ''
    while True:
        line = yield line
        start_delim = re.search(r'^=+', line)
        if not start_delim or start_delim.group() == line:
            continue
        end_delim = re.search(r'=+$', line)
        if not end_delim or end_delim.group() != start_delim.group():
            continue
        level = len(start_delim.group())
        line = f'{"#" * (padding + level)} {line[level:-level].lstrip()}'


@util.prime_coroutine_generator
def format_lists():
    """Transforms ordered and unordered lists into markdown-syntax."""
    ordered_list_history = defaultlist.defaultlist(lambda: 1)
    sequential_empty_lines = 0
    line = ''
    while True:
        line = yield line
        list_item_match = re.match(r'^\s*([-|\+])\s', line)
        if list_item_match:
            i = list_item_match.start(1)
            if line[i] == '-':
                # Un-ordered lists have the same format in markdown.
                pass
            else:
                # Ordered lists must change to the actual number.
                line = f'{line[:i]}{ordered_list_history[i]}.{line[i + 1:]}'
                ordered_list_history[i] += 1
            # Reset numbering of sub-items.
            del ordered_list_history[i + 1:]
        elif line.strip():
            sequential_empty_lines = 0
            ordered_list_history.clear()
        else:
            sequential_empty_lines += 1
            if sequential_empty_lines >= 2:
                ordered_list_history.clear()


@util.prime_coroutine_generator
def format_inner_underscores():
    """Transforms underscores which need to be escaped."""
    line = ''
    while True:
        line = yield line
        inner_underscores = list(_filter_matches(r'(?<=\w)_(?=\w)', line))
        for match in reversed(inner_underscores):
            line = f'{line[:match.start()]}\\_{line[match.end():]}'


def _sub_balanced_delims(delim_pattern, sub, string, **kwargs):
    """Finds paired delimiters and replaces them with a substitution.

    Example:
        >>> _sub_balanced_delims('_', '*', '^_test_$')
        ... '^*test*$'

    Args:
        delim_pattern: regex for the delimiter to replace.
        sub: delimiter to use instead. Can either be a string or a 2-tuple.
        string: string to have delimiters replaced.
        **kwargs: downstream arguments for _filter_matches.

    Returns:
        new string where all targeted balanced delimiters are substituted.
    """
    try:
        start_sub, end_sub = sub
    except ValueError:
        start_sub = end_sub = sub
    delims = _filter_matches(delim_pattern, string, **kwargs)
    balanced_delims = list(zip(delims, delims))
    # Do substitutions in reverse so the match indices stay valid.
    for start_delim, end_delim in reversed(balanced_delims):
        start = string[:start_delim.start()]
        data = string[start_delim.end():end_delim.start()]
        end = string[end_delim.end():]
        string = f'{start}{start_sub}{data}{end_sub}{end}'
    return string


def _filter_matches(pattern, string, preds=None):
    """Returns iterable of matches that pass all of the predicates in `preds`.

    If no predicates are provided, they default to:
        - Match must not appear in link.
        - Match must not appear in backticks.
    """
    if preds is None:
        preds = (_not_in_link, _not_in_backticks)
    return (m for m in re.finditer(pattern, string) if all(p(m) for p in preds))


def _not_in_link(match):
    links = re.finditer(r'\[([^\]]*?) ""(.*?)""\]', match.string)
    return not any(_spans_intersect(match.span(), m.span(2)) for m in links)


def _not_in_backticks(match):
    backticks = re.finditer(r'`.*?`', match.string)
    return not any(_spans_intersect(match.span(), m.span()) for m in backticks)


def _spans_intersect(span1, span2):
    (lo1, hi1), (lo2, hi2) = sorted(span1), sorted(span2)
    return hi1 >= lo2 and hi2 >= lo1
