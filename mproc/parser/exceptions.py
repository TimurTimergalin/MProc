class MProcParseError(Exception):
    message = "unexpected symbol \"{}\""

    def __init__(self, filename, line_number, symbol_number, *args):
        message = ("SyntaxError in {}:{}:{}: " + self.message).format(filename, line_number, symbol_number, *args)
        super().__init__(message)


class MProcStructureError(MProcParseError):
    message = "unexpected flow operator"


class MProcInvalidFlowOperatorError(MProcParseError):
    message = "invalid flow operator: \"{}\""


class MProcTokenExpectedError(MProcParseError):
    message = "token expected"


class MProcEOFError(MProcParseError):
    message = "unexpected end of file"


class MProcInvalidStringLiteral(MProcParseError):
    message = "invalid string literal: \"{}\""
