from .contexts import *

from string import whitespace
from sys import stderr


class Parser:
    whitespace_set = set(whitespace) - {"\n"}

    def __init__(self, filename):
        self.stack = []
        self.line_start = 1
        self.line_end = 1
        self.symbol_start = 0
        self.symbol_end = 0
        self.filename = filename
        self.file = None
        self.inc_line = False

    def exception(self, exc_type, *args, **kwargs):
        return exc_type(self.filename, self.line_start, self.symbol_start, *args, **kwargs)

    def exception_end(self, exc_type, *args, **kwargs):
        return exc_type(self.filename, self.line_end, self.symbol_end, *args, **kwargs)

    def read_symbol(self):
        c = self.file.read(1)
        if self.inc_line:
            self.line_end += 1
            self.symbol_end = 0

        if c:
            self.symbol_end += 1

        self.inc_line = c == "\n"

        return c

    def read_tail_spaces(self, endl_as_whitespace) -> str:
        whitespace_set = self.whitespace_set
        if endl_as_whitespace:
            whitespace_set = whitespace_set | {"\n"}
        while True:
            c = self.read_symbol()
            self.symbol_start = self.symbol_end
            self.line_start = self.line_end
            if c not in whitespace_set:
                return c

    def read_piece(self, delimiters, allow_spaces, endl_as_whitespace, exact_symbols) -> (str, str):
        self.symbol_start = self.symbol_end + 1 if not self.inc_line else 1
        self.line_start = self.line_end + int(self.inc_line)

        if exact_symbols:
            piece = ""
            for i in range(exact_symbols):
                piece += self.read_symbol()

            return piece, None

        c: str
        if allow_spaces:
            c = self.read_tail_spaces(endl_as_whitespace)
        else:
            c = self.read_symbol()

        piece = ""

        can_be_string_literal = False
        first_time = False
        old_delimiters = delimiters
        if c == '"':
            delimiters = {"\n", '"', ''}
            can_be_string_literal = True
            first_time = True

        is_comment = False

        while c not in delimiters or first_time:
            first_time = False
            if c == "/" and not can_be_string_literal:
                is_comment = True
                delimiters = {""}
            elif c == "\n" and is_comment:
                if c in old_delimiters and (not endl_as_whitespace or piece):
                    return piece, c
                delimiters = old_delimiters
                is_comment = False
                if allow_spaces:
                    c = self.read_tail_spaces(endl_as_whitespace)
                continue

            if not is_comment:
                piece += c
            c = self.read_symbol()

        if can_be_string_literal and c != '"':
            raise self.exception(MProcEOFError)

        if can_be_string_literal:
            piece += c
            c = self.read_symbol()
            if c not in old_delimiters:  # noqa
                piece += c
                raise self.exception(MProcInvalidStringLiteral, piece)
            return piece, c

        return piece, c

    def run(self):
        root = RootContext(self)
        self.stack.append(root)

        with open(self.filename) as file:
            self.file = file
            while self.stack:
                context = self.stack[-1]

                try:
                    piece, delimiter = self.read_piece(context.delimiters,
                                                       context.allow_spaces,
                                                       context.endl_as_whitespace,
                                                       context.exact_symbols)
                    context.handle_piece(piece, delimiter)
                except MProcParseError as exc:
                    stderr.write(exc.args[0])
                    stderr.write("\n")
                    stderr.write(f"Stack: {self.stack!r}\n")
                    stderr.write(f"From: {context!r}")
                    exit(1)

        return root.root

    def parse_token(self, piece: str):
        if not piece:
            raise self.exception(MProcTokenExpectedError)

        if piece.startswith('"') and piece.endswith('"'):
            return StringLiteral(self.line_start, self.symbol_start, piece[1:-1])

        try:
            base = 10
            if piece.startswith("0x"):
                base = 16
            elif piece.startswith("0b"):
                base = 2
            return NumericLiteral(self.line_start, self.symbol_start, int(piece, base))
        except ValueError:
            pass

        try:
            return NumericLiteral(
                self.line_start, self.symbol_start,
                float(piece[:-1] if piece.endswith(".") else piece)
            )
        except ValueError:
            pass

        return Token(self.line_start, self.symbol_start, piece)

