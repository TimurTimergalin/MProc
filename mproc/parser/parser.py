from .contexts import *

from string import whitespace
from sys import stderr


class Parser:
    whitespace_set = set(whitespace) - {"\n"}

    def __init__(self, filename):
        self.stack = []  # stack for contexts

        # position in file that was lastly read
        self.line_start = 1
        self.line_end = 1
        self.symbol_start = 0
        self.symbol_end = 0

        # current file
        self.filename = filename
        self.file = None

        # should line number be incremented after reading next symbol
        self.inc_line = False

    def exception(self, exc_type, *args, **kwargs):
        """Generates an exception with filename, line and symbol number passed as additional arguments"""
        return exc_type(self.filename, self.line_start, self.symbol_start, *args, **kwargs)

    def exception_end(self, exc_type, *args, **kwargs):
        """Same as exception, but line and symbol are line_end and symbol_end"""
        return exc_type(self.filename, self.line_end, self.symbol_end, *args, **kwargs)

    def read_symbol(self):
        """Reads the next symbol from file, incrementing symbol_end and line_end if needed"""
        c = self.file.read(1)
        if self.inc_line:
            self.line_end += 1
            self.symbol_end = 0

        if c:  # if it is not EOF
            self.symbol_end += 1

        self.inc_line = c == "\n"

        return c

    def read_head_spaces(self, endl_as_whitespace) -> str:
        """
        Reads all whitespace symbols before actual piece of code.
        :param endl_as_whitespace - if true, \\n counts as whitespace symbol as well
        """
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
        """
        Reads the next piece of code
        :param delimiters: set of symbols indicating the end of a piece code
        :param allow_spaces: if true, all whitespace symbols before actual piece of code will be
        omitted (see Parser.read_head_spaces
        :param endl_as_whitespace: param for Parser.read_head_spaces
        :param exact_symbols: if value is non-zero, exact symbols mode will be used instead of standard procedure:
        the amount of symbols given will be indefinitely read and returned as a piece (delimiter will be None)
        :returns a tuple that contains piece of code read and the delimiter that stopped the reading
        """

        # reset the counters
        self.symbol_start = self.symbol_end + 1 if not self.inc_line else 1
        self.line_start = self.line_end + int(self.inc_line)

        if exact_symbols:  # exact symbol mode
            piece = ""
            for i in range(exact_symbols):
                piece += self.read_symbol()

            return piece, None

        c: str
        if allow_spaces:
            c = self.read_head_spaces(endl_as_whitespace)
        else:
            c = self.read_symbol()

        piece = ""

        is_string_literal = False
        first_time = False
        old_delimiters = delimiters
        if c == '"':
            delimiters = {"\n", '"', ''}  # read the string until literal or line/file ends
            is_string_literal = True  # if it starts with " it has to be a string literal
            first_time = True  # to avoid not entering a loop

        is_comment = False  # for skipping comments

        while c not in delimiters or first_time:  # if first time is true, " has already been read
            first_time = False
            if c == "/" and not is_string_literal:  # comment mode
                is_comment = True
                delimiters = {""}  # stop only at EOF (\n will be handled in the loop)
            elif c == "\n" and is_comment:  # ending comment mode
                if c in old_delimiters and (not endl_as_whitespace or piece):
                    # if comment was not during skipping head spaces mode
                    return piece, c

                # if comment was during skipping head spaces, continue doing so
                delimiters = old_delimiters
                is_comment = False
                if allow_spaces:
                    c = self.read_head_spaces(endl_as_whitespace)
                continue

            if not is_comment:
                piece += c  # add a symbol to the piece
            c = self.read_symbol()

        if is_string_literal and c != '"':  # string literals have to end with " (multiple lines string are not allowed)
            raise self.exception(MProcEOFError)

        if is_string_literal:  # reading delimiter after string literal
            piece += c
            c = self.read_symbol()
            if c not in old_delimiters:  # if it is not in delimiters, raise an error
                piece += c
                raise self.exception(MProcInvalidStringLiteral, piece)
            return piece, c

        return piece, c

    def run(self):
        """Execute the parsing process"""
        root = RootContext(self)
        self.stack.append(root)  # add root context as a starting point

        with open(self.filename) as file:
            self.file = file
            while self.stack:
                context = self.stack[-1]  # get last context

                try:
                    # read a piece and pass to the context

                    piece, delimiter = self.read_piece(context.delimiters,
                                                       context.allow_spaces,
                                                       context.endl_as_whitespace,
                                                       context.exact_symbols)
                    context.handle_piece(piece, delimiter)
                except MProcParseError as exc:  # pretty exception
                    stderr.write(exc.args[0])
                    stderr.write("\n")
                    exit(0)  # although parsing process has finished with an error, the python program itself finished
                    # properly

        return root.root  # syntax tree stored here

    def parse_token(self, piece: str):
        """Return a token, numerical or string literal based on the string it is represented by"""
        if not piece:  # empty is not allowed
            raise self.exception(MProcTokenExpectedError)

        if piece.startswith('"') and piece.endswith('"'):  # string literal
            return StringLiteral(self.line_start, self.symbol_start, piece[1:-1])

        try:  # integer numerical literal
            # bases 10, 16 and 2 supported
            base = 10
            if piece.startswith("0x"):
                base = 16
            elif piece.startswith("0b"):
                base = 2
            return NumericLiteral(self.line_start, self.symbol_start, int(piece, base))
        except ValueError:
            pass

        try:  # float numerical literal
            return NumericLiteral(
                self.line_start, self.symbol_start,
                float(piece[:-1] if piece.endswith(".") else piece)  # that is how mlog parses float literals
                # i.e, 2.2. is 2.2 in mlog
            )
        except ValueError:
            pass

        return Token(self.line_start, self.symbol_start, piece)  # otherwise, it is a token
