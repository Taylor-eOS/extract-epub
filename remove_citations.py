import sys
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Optional

class TokenKind(Enum):
    TEXT = auto()
    OPEN = auto()
    CLOSE = auto()

@dataclass
class Token:
    kind: TokenKind
    char: str
    position: int

@dataclass
class ParenSpan:
    start: int
    end: int
    inner: str
    outer: str

@dataclass
class ScoredSpan:
    span: ParenSpan
    score: float
    evidence: list[str] = field(default_factory=list)

def tokenize(text):
    tokens = []
    for i, ch in enumerate(text):
        if ch == '(':
            tokens.append(Token(TokenKind.OPEN, ch, i))
        elif ch == ')':
            tokens.append(Token(TokenKind.CLOSE, ch, i))
        else:
            tokens.append(Token(TokenKind.TEXT, ch, i))
    return tokens

def extract_balanced_spans(tokens, text):
    spans = []
    stack = []
    for token in tokens:
        if token.kind == TokenKind.OPEN:
            stack.append(token.position)
        elif token.kind == TokenKind.CLOSE:
            if not stack:
                continue
            open_pos = stack.pop()
            close_pos = token.position
            inner = text[open_pos + 1:close_pos]
            outer = text[open_pos:close_pos + 1]
            spans.append(ParenSpan(
                start=open_pos,
                end=close_pos + 1,
                inner=inner,
                outer=outer,
            ))
    return spans

def normalize(s):
    return ' '.join(s.split())

def extract_numeric_tokens(s):
    results = []
    current = []
    for ch in s:
        if ch.isdigit():
            current.append(ch)
        else:
            if current:
                results.append(''.join(current))
                current = []
    if current:
        results.append(''.join(current))
    return results

def extract_numeric_tokens_with_positions(s):
    results = []
    current = []
    start = None
    for i, ch in enumerate(s):
        if ch.isdigit():
            if start is None:
                start = i
            current.append(ch)
        else:
            if current:
                results.append((''.join(current), start, i))
                current = []
                start = None
    if current:
        results.append((''.join(current), start, len(s)))
    return results

def classify_numeric_tokens(numeric_tokens):
    return classify_numeric_tokens_from_text(None, numeric_tokens)

def classify_numeric_tokens_from_text(text, numeric_tokens):
    if text is None:
        years = []
        pages = []
        for tok in numeric_tokens:
            if len(tok) == 4:
                n = int(tok)
                if 1000 <= n <= 2100:
                    years.append(n)
                    continue
            n = int(tok)
            if 1 <= n <= 999:
                pages.append(n)
        return years, pages
    tokens_with_pos = extract_numeric_tokens_with_positions(text)
    years = []
    pages = []
    dash_chars = {'-', '\u2013', '\u2014'}
    skip_indices = set()
    for i, (tok, start, end) in enumerate(tokens_with_pos):
        if i in skip_indices:
            continue
        if len(tok) == 4:
            n = int(tok)
            if 1000 <= n <= 2100:
                years.append(n)
                if i + 1 < len(tokens_with_pos):
                    next_tok, next_start, next_end = tokens_with_pos[i + 1]
                    between = text[end:next_start]
                    if between and all(ch in dash_chars for ch in between) and len(next_tok) <= 4:
                        skip_indices.add(i + 1)
                continue
        n = int(tok)
        if 1 <= n <= 999:
            pages.append(n)
    return years, pages

def extract_word_tokens(s):
    words = []
    current = []
    for ch in s:
        if ch.isalpha() or ch == "'":
            current.append(ch)
        else:
            if current:
                words.append(''.join(current))
                current = []
    if current:
        words.append(''.join(current))
    return words

def count_punctuation_classes(s):
    found = set()
    for ch in s:
        if ch == ':':
            found.add('colon')
        elif ch == ';':
            found.add('semicolon')
        elif ch == ',':
            found.add('comma')
    return found

def looks_like_author_name(word):
    if not word:
        return False
    if not word[0].isupper():
        return False
    if len(word) < 3:
        return False
    if not all(ch.isalpha() or ch == "'" for ch in word):
        return False
    return True

def looks_like_latin_abbreviation(word):
    latin = {'ibid', 'op', 'cit', 'loc', 'et', 'al', 'idem', 'cf', 'viz', 'sic'}
    return word.lower() in latin

CITATION_CONNECTIVES = {'and', 'see', 'also', 'in', 'cf', 'e', 'g', 'i', 'b', 'a'}

def score_span(span):
    text = normalize(span.inner)
    score = 0.0
    evidence = []
    if not text:
        return ScoredSpan(span=span, score=0.0, evidence=['empty content'])
    if len(text) > 200:
        return ScoredSpan(span=span, score=0.0, evidence=['too long to be a citation'])
    numeric_tokens = extract_numeric_tokens(text)
    years, pages = classify_numeric_tokens_from_text(text, numeric_tokens)
    word_tokens = extract_word_tokens(text)
    punct_classes = count_punctuation_classes(text)
    latin_words = [w for w in word_tokens if looks_like_latin_abbreviation(w)]
    if latin_words:
        return ScoredSpan(span=span, score=1000.0, evidence=[f'latin citation abbreviation forces acceptance: {latin_words}'])
    if not years:
        return ScoredSpan(span=span, score=0.0, evidence=['no year present — required for citation'])
    lowercase_words = [w for w in word_tokens if w[0].islower() and w.lower() not in CITATION_CONNECTIVES]
    author_words = [w for w in word_tokens if looks_like_author_name(w)]
    total_words = len(word_tokens)
    lowercase_count = len(lowercase_words)
    if total_words > 0:
        lowercase_ratio = lowercase_count / total_words
    else:
        lowercase_ratio = 0.0
    if lowercase_ratio > 0.35:
        return ScoredSpan(span=span, score=0.0, evidence=[
            f'too many lowercase words ({lowercase_count}/{total_words} = {lowercase_ratio:.0%}), looks like prose'
        ])
    if lowercase_count > 3:
        return ScoredSpan(span=span, score=0.0, evidence=[
            f'too many lowercase words in absolute terms ({lowercase_count}): {lowercase_words}'
        ])
    score += 40.0
    evidence.append(f'contains year(s): {years}')
    if not author_words and not pages:
        return ScoredSpan(span=span, score=0.0, evidence=['year only, no author or page number — too ambiguous'])
    if author_words:
        score += 25.0
        evidence.append(f'author-like capitalized words: {author_words}')
    if pages:
        score += 15.0
        evidence.append(f'contains page number(s): {pages}')
    if 'colon' in punct_classes:
        score += 10.0
        evidence.append('colon present (page separator)')
    if 'semicolon' in punct_classes:
        score += 8.0
        evidence.append('semicolon present (citation list separator)')
    if total_words > 12:
        penalty = (total_words - 12) * 4.0
        score -= penalty
        evidence.append(f'penalized for high word count ({total_words} words, -{penalty:.1f})')
    return ScoredSpan(span=span, score=score, evidence=evidence)

def resolve_overlapping_spans(scored_spans):
    sorted_spans = sorted(scored_spans, key=lambda s: s.score, reverse=True)
    accepted = []
    covered = set()
    for ss in sorted_spans:
        positions = set(range(ss.span.start, ss.span.end))
        if positions & covered:
            continue
        accepted.append(ss)
        covered |= positions
    return accepted

def remove_accepted_spans(text, accepted_spans):
    removal_ranges = sorted(
        [(ss.span.start, ss.span.end) for ss in accepted_spans],
        key=lambda r: r[0],
        reverse=True
    )
    chars = list(text)
    for start, end in removal_ranges:
        chars[start:end] = []
    return ''.join(chars)

def collapse_leftover_whitespace(text):
    lines = text.splitlines(keepends=True)
    result = []
    for line in lines:
        ending = ''
        if line.endswith('\r\n'):
            ending = '\r\n'
            line = line[:-2]
        elif line.endswith('\n'):
            ending = '\n'
            line = line[:-1]
        elif line.endswith('\r'):
            ending = '\r'
            line = line[:-1]
        words = line.split()
        result.append(' '.join(words) + ending)
    return ''.join(result)

def process_file(path, threshold=40.0, dry_run=False):
    with open(path, 'r', encoding='utf-8') as f:
        text = f.read()
    tokens = tokenize(text)
    spans = extract_balanced_spans(tokens, text)
    scored = [score_span(span) for span in spans]
    candidates = [ss for ss in scored if ss.score >= threshold]
    accepted = resolve_overlapping_spans(candidates)
    print(f"Scanned {len(spans)} parenthesized span(s), "
          f"{len(candidates)} passed threshold, "
          f"{len(accepted)} accepted after overlap resolution.")
    for ss in sorted(accepted, key=lambda s: s.span.start):
        print(f"  [{ss.span.start}:{ss.span.end}] score={ss.score:.1f} | {ss.span.outer!r}")
        for e in ss.evidence:
            print(f"    · {e}")
    if dry_run:
        print("Dry run — no file written.")
        return
    cleaned = remove_accepted_spans(text, accepted)
    cleaned = collapse_leftover_whitespace(cleaned)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(cleaned)
    print(f"Written: {path}")

if __name__ == '__main__':
    path = input('Input file (input.txt): ') or 'input.txt'
    dry_run = '--dry-run' in sys.argv
    process_file(path, dry_run=dry_run)
