class MProcParseError(Exception):
    """Base error of parsing"""
    message = "unexpected symbol \"{}\""

    def __init__(self, filename, line_number, symbol_number, *args):
        message = ("SyntaxError in {}:{}:{}: " + self.message).format(filename, line_number, symbol_number, *args)
        super().__init__(message)


class MProcStructureError(MProcParseError):
    """Raised when unexpected # is met during parsing"""
    message = "unexpected flow operator"


class MProcInvalidFlowOperatorError(MProcParseError):
    """Raised when flow operator with invalid name is used"""
    message = "invalid flow operator: \"{}\""


class MProcTokenExpectedError(MProcParseError):
    """Raised when the token is not passed when it is expected"""
    message = "token expected"


class MProcEOFError(MProcParseError):
    """Raised when file ended before a block/string literal has been closed"""
    message = "unexpected end of file"


class MProcInvalidStringLiteral(MProcParseError):
    """Raised during string literals parsing"""
    message = "invalid string literal: \"{}\""
