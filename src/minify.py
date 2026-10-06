"""Small, conservative minifier for this app's own code (no external tools needed).

JavaScript: removes comments and indentation, keeps a newline wherever the original had one
between tokens (so automatic semicolon insertion behaves exactly as before), and only keeps a
space where two tokens would otherwise merge. Strings, template literals (including ${...}) and
regular expressions are copied untouched.
"""
import re

ID = re.compile(r'[A-Za-z0-9_$\u0080-\uffff]')
NUM = re.compile(r'0[xXbBoO][0-9a-fA-F_]+n?|(?:\d[\d_]*(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?n?')
REGEX_AFTER_WORDS = {'return', 'typeof', 'instanceof', 'in', 'of', 'new', 'delete', 'void',
                     'throw', 'case', 'do', 'else', 'yield', 'await'}


class JSMinifier:
    def __init__(self, src):
        self.s = src
        self.n = len(src)
        self.out = []
        self.last = ''          # last significant token emitted
        self.pending_nl = False

    def emit(self, tok):
        prev = self.out[-1] if self.out else ''
        if self.pending_nl and self.out:
            self.out.append('\n')
        elif prev:
            a, b = prev[-1], tok[0]
            if (ID.match(a) and ID.match(b)) or (a == b and a in '+-') or (a == '/' and b in '/*') \
                    or (a == '.' and b.isdigit()) or (prev.isdigit() and b == '.'):
                self.out.append(' ')
        self.out.append(tok)
        self.pending_nl = False
        self.last = tok

    def regex_allowed(self):
        t = self.last
        if not t:
            return True
        if ID.match(t[-1]):
            return t in REGEX_AFTER_WORDS
        return t[-1] not in ')]}'

    def read_string(self, i):
        q = self.s[i]; j = i + 1
        while j < self.n:
            c = self.s[j]
            if c == '\\': j += 2; continue
            if c == q: return j + 1
            if c == '\n': raise ValueError('unterminated string at %d' % i)
            j += 1
        raise ValueError('unterminated string at %d' % i)

    def read_regex(self, i):
        j = i + 1; in_class = False
        while j < self.n:
            c = self.s[j]
            if c == '\\': j += 2; continue
            if c == '\n': raise ValueError('unterminated regex at %d' % i)
            if in_class:
                if c == ']': in_class = False
            elif c == '[': in_class = True
            elif c == '/':
                j += 1
                while j < self.n and ID.match(self.s[j]): j += 1   # flags
                return j
            j += 1
        raise ValueError('unterminated regex at %d' % i)

    def read_template(self, i):
        """Returns (text, end). Text inside ${...} is minified recursively."""
        parts = ['`']; j = i + 1; start = j
        while j < self.n:
            c = self.s[j]
            if c == '\\': j += 2; continue
            if c == '`':
                parts.append(self.s[start:j + 1]); return ''.join(parts), j + 1
            if c == '$' and j + 1 < self.n and self.s[j + 1] == '{':
                parts.append(self.s[start:j + 2])
                sub = JSMinifier(self.s); sub.n = self.n
                end = sub.run(j + 2, stop_at_brace=True)
                parts.append(''.join(sub.out).replace('\n', ' '))
                parts.append('}')
                j = end; start = j
                continue
            j += 1
        raise ValueError('unterminated template at %d' % i)

    def run(self, i=0, stop_at_brace=False):
        s, depth = self.s, 0
        while i < self.n:
            c = s[i]
            if c in ' \t\r\n':
                if c == '\n': self.pending_nl = True
                i += 1; continue
            if s.startswith('//', i):
                j = s.find('\n', i); i = self.n if j < 0 else j
                continue
            if s.startswith('/*', i):
                j = s.find('*/', i + 2)
                if j < 0: raise ValueError('unterminated comment')
                if '\n' in s[i:j]: self.pending_nl = True
                i = j + 2; continue
            if c in '"\'':
                j = self.read_string(i); self.emit(s[i:j]); i = j; continue
            if c == '`':
                text, j = self.read_template(i); self.emit(text); i = j; continue
            if c == '/' and self.regex_allowed():
                j = self.read_regex(i); self.emit(s[i:j]); i = j; continue
            m = NUM.match(s, i) if (c.isdigit() or (c == '.' and i + 1 < self.n and s[i + 1].isdigit())) else None
            if m:
                self.emit(m.group(0)); i = m.end(); continue
            if ID.match(c):
                j = i + 1
                while j < self.n and ID.match(s[j]): j += 1
                self.emit(s[i:j]); i = j; continue
            if stop_at_brace:
                if c == '{': depth += 1
                elif c == '}':
                    if depth == 0: return i + 1
                    depth -= 1
            # punctuation: keep multi-char operators together exactly as written
            j = i + 1
            while j < self.n and s[j] in '=<>!&|+-*%^?.:' and s[i] in '=<>!&|+-*%^?.:' and s[j] not in ':':
                j += 1
            self.emit(s[i:j]); i = j
        if stop_at_brace:
            raise ValueError('unclosed ${')
        return i


def minify_js(src):
    m = JSMinifier(src); m.run()
    return ''.join(m.out).strip()


def minify_css(css):
    css = re.sub(r'/\*.*?\*/', '', css, flags=re.S)
    css = re.sub(r'\s+', ' ', css)
    css = re.sub(r'\s*([{};,>])\s*', r'\1', css)
    css = css.replace(';}', '}')
    return css.strip()


def minify_html(html):
    html = re.sub(r'<!--.*?-->', '', html, flags=re.S)
    html = re.sub(r'\n[ \t]+', '\n', html)
    html = re.sub(r'\n{2,}', '\n', html)
    return html.strip() + '\n'
