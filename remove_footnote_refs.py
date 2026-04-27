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

def classify_numeric_tokens(numeric_tokens):
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

def score_span(span):
    text = normalize(span.inner)
    score = 0.0
    evidence = []
    if not text:
        return ScoredSpan(span=span, score=0.0, evidence=['empty content'])
    if len(text) > 150:
        return ScoredSpan(span=span, score=0.0, evidence=['too long to be a citation'])
    numeric_tokens = extract_numeric_tokens(text)
    years, pages = classify_numeric_tokens(numeric_tokens)
    word_tokens = extract_word_tokens(text)
    punct_classes = count_punctuation_classes(text)
    if not numeric_tokens:
        return ScoredSpan(span=span, score=0.0, evidence=['no numeric content'])
    if years:
        score += 40.0
        evidence.append(f'contains year(s): {years}')
    if pages:
        score += 15.0
        evidence.append(f'contains page number(s): {pages}')
    author_words = [w for w in word_tokens if looks_like_author_name(w)]
    if author_words:
        score += 20.0
        evidence.append(f'author-like capitalized words: {author_words}')
    latin_words = [w for w in word_tokens if looks_like_latin_abbreviation(w)]
    if latin_words:
        score += 25.0
        evidence.append(f'latin citation abbreviations: {latin_words}')
    if 'colon' in punct_classes:
        score += 10.0
        evidence.append('colon present (page separator)')
    if 'semicolon' in punct_classes:
        score += 8.0
        evidence.append('semicolon present (citation list separator)')
    total_chars = len(text)
    alpha_chars = sum(1 for ch in text if ch.isalpha())
    digit_chars = sum(1 for ch in text if ch.isdigit())
    space_chars = sum(1 for ch in text if ch == ' ')
    prose_chars = total_chars - alpha_chars - digit_chars - space_chars
    word_count = len(word_tokens)
    if word_count > 15:
        penalty = (word_count - 15) * 3.0
        score -= penalty
        evidence.append(f'penalized for high word count ({word_count} words, -{penalty:.1f})')
    if prose_chars > total_chars * 0.3:
        score -= 15.0
        evidence.append('high proportion of non-citation punctuation, likely prose')

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
    path = input('Input file: ') or 'input.txt'
    dry_run = '--dry-run' in sys.argv
    process_file(path, dry_run=dry_run)

