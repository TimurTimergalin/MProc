from abc import ABC, abstractmethod

from .exceptions import *
from ..syntax_tree import *

from string import whitespace


class Context(ABC):
    """Base parse context class"""

    def __init__(self, parser):
        self.parser = parser

    @abstractmethod
    def handle_piece(self, piece, delimiter):
        pass

    @abstractmethod
    def handle_child_content(self, content, delimiter=None):
        pass

    def save_statement(self, token, delimiter=None):
        self.parser.stack.pop()
        parent = self.parser.stack[-1]
        parent.handle_child_content(token, delimiter)

    def create_assignment(self, token):
        if token is None:
            raise self.parser.exception(MProcTokenExpectedError)
        self.parser.stack.append(RightHandSideContext(token, self.parser))

    def create_list(self, token):
        if token is None:
            raise self.parser.exception(MProcTokenExpectedError)
        self.parser.stack.append(ListContext(token, self.parser))

    def create_call(self, token):
        if token is None:
            raise self.parser.exception(MProcTokenExpectedError)
        self.parser.stack.append(CallContext(token, self.parser))

    def create_flow_operator(self):
        self.parser.stack.append(ExpectedFlowOperatorContext(self.parser))

    def skip_spaces(self, token, endl_as_whitespace=False):
        self.parser.stack.append(SkipSpacesContext(token, endl_as_whitespace, self.parser))

    def wrong_delimiter(self, delimiter):
        raise self.parser.exception_end(MProcParseError, delimiter)

    whitespace_set = set(whitespace) - {'\n'}

    delimiters = whitespace_set | set("#\n=,()") | {""}

    allow_spaces = True

    endl_as_whitespace = False

    exact_symbols = 0

    def __repr__(self):
        return self.__class__.__name__


class RootContext(Context):
    """Context that is always at the bottom of the stack, containing the resulting syntax tree"""
    delimiters = Context.delimiters

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.root = Root(body=[], line=1, symbol=1)

    def handle_piece(self, piece, delimiter):
        if delimiter == "" and not piece:  # if the file is ended, finish the program
            self.parser.stack.pop()
            return

        # read the next statement
        self.parser.stack.append(selc := SkipEmptyLinesContext(self.parser))
        selc.handle_piece(piece, delimiter)

    def handle_child_content(self, content, delimiter=None):
        self.root.body.append(content)
        if delimiter != "":
            # leave next piece for the next statement
            self.parser.stack.append(SkipEmptyLinesContext(self.parser))
        else:
            self.parser.stack.pop()  # if the file is ended, finish the program


class SkipEmptyLinesContext(Context):
    """Context for parsing empty lines before parsing a new statement"""

    def handle_piece(self, piece, delimiter):
        if piece or delimiter not in '\n':  # if something is met
            # create a new statement
            self.parser.stack.pop()
            self.parser.stack.append(nsc := NewStatementContext(self.parser))
            nsc.handle_piece(piece, delimiter)

        elif delimiter == "":
            self.parser.stack.pop()  # root context will finish anyway

    def handle_child_content(self, content, delimiter=None):
        pass


class NewStatementContext(Context):
    """Context for parsing new statement"""

    def handle_piece(self, piece, delimiter):
        if delimiter == "#":
            if piece:
                # No token can be before flow operator
                raise self.parser.exception(MProcStructureError)
            self.create_flow_operator()
            return
        token = self.parser.parse_token(piece)
        if delimiter in '\n':  # \n or empty
            # in this case statement is just a token
            # for example, here:
            #
            # #def
            # switch1
            # #enddef
            #
            # second line is a "token statement"
            self.save_statement(token, delimiter if delimiter == "" else None)

        elif delimiter in self.whitespace_set:
            # in this case we do not know what should be done with the token, so we pass it to SkipSpacesContext
            self.skip_spaces(token)

        elif delimiter == '=':
            # in this case we know it is an assignment statement
            self.create_assignment(token)

        elif delimiter == ")":
            # that is a syntax error
            self.wrong_delimiter(delimiter)

        elif delimiter == ",":
            self.create_list(token)

        elif delimiter == "(":
            self.create_call(token)

    def handle_child_content(self, content, delimiter=None):
        if delimiter is None:
            # in this case child has completely finished parsing but the line has not ended yet
            self.skip_spaces(content)
        elif delimiter in '\n':  # \n or empty
            # finish parsing
            self.save_statement(content, delimiter if not delimiter else None)
        elif delimiter == "=":
            self.create_assignment(content)
        elif delimiter == ",":
            self.create_list(content)

        elif delimiter == ")":
            self.wrong_delimiter(delimiter)

        elif delimiter == "(":
            self.create_call(content)


class SkipSpacesContext(Context):
    """Context for finding new non-whitespace content"""

    def __init__(self, token, endl_as_whitespace=False, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.token = token
        self.endl_as_whitespace = endl_as_whitespace

    def handle_piece(self, piece, delimiter):
        if piece and self.token is not None:
            # There can be no two consecutive tokens
            raise self.parser.exception(MProcParseError, piece)
        if delimiter == "#":
            # No flow operators are allowed after tokens
            raise self.parser.exception_end(MProcStructureError)

        # If everything is fine we let the parent handle the business
        self.parser.stack.pop()
        parent = self.parser.stack[-1]
        token = self.parser.parse_token(piece) if piece else None
        parent.handle_child_content(self.token or token, delimiter)

    def handle_child_content(self, content, delimiter=None):
        assert 0, "SkipSpacesContext may not have children"


class RightHandSideContext(Context):
    """Context for parsing right hand side of assignment statement"""

    endl_as_whitespace = True

    def __init__(self, lhs, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.lhs = lhs

    def save_statement(self, token, delimiter=None):
        if token is None:
            raise self.parser.exception(MProcTokenExpectedError)
        content = Assignment(lhs=self.lhs, rhs=token, line=self.lhs.line, symbol=self.lhs.symbol)
        super().save_statement(content, delimiter)

    def handle_piece(self, piece, delimiter):
        token = self.parser.parse_token(piece) if piece else None
        if delimiter in "\n)":  # empty too
            # in this case we know that the right hand side expression is just a variable/literal
            self.save_statement(token, delimiter)

        elif delimiter in self.whitespace_set:
            self.skip_spaces(token)

        elif delimiter == "#":
            raise self.parser.exception_end(MProcStructureError)

        elif delimiter in "=":
            self.wrong_delimiter(delimiter)

        elif delimiter == ",":
            if token is None:
                raise self.parser.exception(MProcTokenExpectedError)
            self.create_list(token)

        elif delimiter == "(":
            self.create_call(token)

    def handle_child_content(self, content, delimiter=None):
        if delimiter is None:
            self.skip_spaces(content)
        elif delimiter in "\n":  # empty too
            if delimiter == "\n" and not content:  # if nothing is read yet, we search on the next line.
                # this way multiple-line assignments are allowed
                self.skip_spaces(None, True)
            else:
                self.save_statement(content, delimiter)

        elif delimiter in "=)":
            self.wrong_delimiter(delimiter)

        elif delimiter == ",":
            if content is None:
                raise self.parser.exception(MProcTokenExpectedError)
            self.create_list(content)

        elif delimiter == "(":
            self.create_call(content)


class NamedArgumentRightHandSideContext(RightHandSideContext):
    """Context for parsing naming argument's right hand side, (i.e. func(a=3))"""

    def create_list(self, token):
        # while inside function call, argument lists must be created and not the usual ones
        content = Assignment(lhs=self.lhs, rhs=token, line=self.lhs.line, symbol=self.lhs.symbol)
        self.parser.stack.pop()
        self.parser.stack.append(ArgumentListContext(content, self.parser))


class ExpectedFlowOperatorContext(Context):
    """Context for reading names of flow operators"""

    self_sufficient_operators = {
        "break": Break,
        "continue": Continue,
        "end": End,
        "stop": Stop,
    }

    expression_required_operators = {
        "import": Import,
        "wait": Wait,
        "using": Using,
        "var": Var
    }

    expression_allowed_operators = {
        "return": Return,
    }

    simple_block_operators = {
        "def": Def,
        "init": Init,
        "prog": Prog,
        "link": Link
    }

    block_end_operators = {
        "endprog": Prog,
        "endfunc": Func,
        "endrawfunc": RawFunc,
        "endif": If,
        "endloop": Loop,
        "enddef": Def,
        "endinit": Init,
        "endmlog": MLog,
        "endenum": Enum,
        "endlink": Link
    }

    block_with_expression_operators = {
        "if": If,
        "loop": Loop
    }

    body_switch_operators = {
        "else": If,
        "after": Loop
    }

    function_operators = {
        "func": Func,
        "enum": Enum,
    }

    raw_func_operators = {
        "rawfunc": RawFunc
    }

    mlog_operators = {
        "mlog": MLog
    }

    allow_spaces = False

    def handle_piece(self, piece, delimiter):
        if delimiter not in self.whitespace_set | set("\n") | {""}:
            # There can be no other delimiters (so ',', #, =, (, ) are not allowed)
            self.wrong_delimiter(delimiter)

        # replace with required flow operator context

        self.parser.stack.pop()

        if piece in self.self_sufficient_operators:
            content = self.self_sufficient_operators[piece](self.parser.line_start, self.parser.symbol_start - 1)
            self.parser.stack.append(ctx := SelfSufficientFlowOperatorContext(content, self.parser))
        elif piece in self.expression_required_operators:
            content = self.expression_required_operators[piece](self.parser.line_start, self.parser.symbol_start - 1,
                                                                None)
            self.parser.stack.append(ctx := ExpressionAllowedFlowOperatorContext(content, True,
                                                                                 self.parser))
        elif piece in self.expression_allowed_operators:
            content = self.expression_allowed_operators[piece](self.parser.line_start, self.parser.symbol_start - 1,
                                                               None)
            self.parser.stack.append(ctx := ExpressionAllowedFlowOperatorContext(content, False,
                                                                                 self.parser))
        elif piece in self.simple_block_operators:
            content = self.simple_block_operators[piece](self.parser.line_start, self.parser.symbol_start - 1, [])
            self.parser.stack.append(ctx := SimpleBlockFlowOperatorContext(content, self.parser))
        elif piece in self.block_end_operators:
            content_type = self.block_end_operators[piece]
            self.parser.stack.append(ctx := BlockEndFlowOperatorContext(content_type, piece, self.parser))
        elif piece in self.block_with_expression_operators:
            content = self.block_with_expression_operators[piece](self.parser.line_start, self.parser.symbol_start - 1,
                                                                  None, [], [])
            self.parser.stack.append(ctx := BlockWithExpressionFlowOperatorContext(content, self.parser))
        elif piece in self.body_switch_operators:
            content_type = self.body_switch_operators[piece]
            self.parser.stack.append(ctx := BodySwitchFlowOperatorContext(content_type, piece, self.parser))
        elif piece in self.function_operators:
            content = self.function_operators[piece](self.parser.line_start, self.parser.symbol_start - 1, None, [])
            self.parser.stack.append(ctx := FunctionFlowOperatorContext(content, self.parser))
        elif piece in self.raw_func_operators:
            content = self.raw_func_operators[piece](self.parser.line_start, self.parser.symbol_start - 1, None, "")
            self.parser.stack.append(ctx := RawFunctionFlowOperatorContext(content, self.parser))
        elif piece in self.mlog_operators:
            content = self.mlog_operators[piece](self.parser.line_start, self.parser.symbol_start - 1, "")
            self.parser.stack.append(ctx := MLogBlockFlowOperatorContext(content, self.parser))
        else:
            raise self.parser.exception(MProcInvalidFlowOperatorError, piece)

        if delimiter in "\n":
            ctx.handle_piece("", delimiter)

    def handle_child_content(self, content, delimiter=None):
        assert 0, "ExpectedFlowOperatorContext may not have children"


class SelfSufficientFlowOperatorContext(Context):
    delimiters = set("\n") | {""}

    def __init__(self, content, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.content = content

    def handle_piece(self, piece, delimiter):
        if piece:
            # There can be nothing after self-sufficient flow operator
            raise self.parser.exception(MProcParseError, piece)

        self.save_statement(self.content, delimiter)

    def handle_child_content(self, content, delimiter=None):
        assert 0, "SelfSufficientFlowOperatorContext may not have children"


class ExpressionAllowedFlowOperatorContext(Context):
    def __init__(self, content, required, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.content = content
        self.required = required

    def save_statement(self, token, delimiter=None):
        self.content.expression = token
        super().save_statement(self.content, delimiter)

    def handle_piece(self, piece, delimiter):
        token = self.parser.parse_token(piece) if piece else None

        if token is None and self.required:  # if expression is required, but absent
            raise self.parser.exception(MProcTokenExpectedError)

        if delimiter in "\n":  # empty too
            self.save_statement(token, delimiter)

        elif delimiter in self.whitespace_set:
            self.skip_spaces(token)

        elif delimiter in ")#":
            raise self.parser.exception_end(MProcParseError, delimiter)

        elif delimiter == "=":
            self.create_assignment(token)

        elif delimiter == ",":
            self.create_list(token)

        elif delimiter == "(":
            self.create_call(token)

    def handle_child_content(self, content, delimiter=None):
        if delimiter is None:
            self.skip_spaces(content)
        elif delimiter in "\n":  # empty too
            self.save_statement(content, delimiter)

        elif delimiter in ")":
            raise self.parser.exception_end(MProcParseError, delimiter)

        elif delimiter == "=":
            self.create_assignment(content)

        elif delimiter == ",":
            self.create_list(content)

        elif delimiter == "(":
            self.create_call(content)


class SimpleBlockFlowOperatorContext(Context):
    delimiters = set("\n") | {""}

    def __init__(self, content, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.content = content

    def append(self, content):
        self.content.body.append(content)

    def read_statement(self):
        self.parser.stack.append(SkipEmptyLinesContext(self.parser))

    def handle_piece(self, piece, delimiter):
        if piece:
            raise self.parser.exception(MProcParseError, piece)

        if delimiter == "":
            raise self.parser.exception(MProcEOFError)
        else:  # always \n
            self.read_statement()

    def handle_child_content(self, content, delimiter=None):
        if delimiter is None:
            self.append(content)
            self.read_statement()
        elif delimiter == "":
            raise self.parser.exception(MProcEOFError)
        else:  # always \n
            self.read_statement()


class MLogBlockFlowOperatorContext(SimpleBlockFlowOperatorContext):
    def append(self, content):
        self.content.body += content

    def read_statement(self):
        self.parser.stack.append(MLogContext(self.parser))


class BlockEndFlowOperatorContext(Context):
    delimiters = set("\n") | {""}

    def __init__(self, content_type, name, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.content_type = content_type
        self.name = name

    def handle_piece(self, piece, delimiter):
        if piece:
            raise self.parser.exception(MProcParseError, piece)

        self.parser.stack.pop()
        nsc = self.parser.stack.pop()
        assert isinstance(nsc, NewStatementContext), self.parser.stack  # should always be true in prod

        block_context = self.parser.stack[-1]
        if not hasattr(block_context, "content") or not isinstance(block_context.content, self.content_type):
            raise self.parser.exception(MProcParseError, "#" + self.name)

        block_context.save_statement(block_context.content, delimiter)

    def handle_child_content(self, content, delimiter=None):
        assert 0, "BlockEndFlowOperatorContext may not have children"


class BlockWithExpressionFlowOperatorContext(Context):
    def __init__(self, content, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.content = content
        self.body2 = False
        self.reading_expression = True

    def append(self, content):
        if content is None:
            return
        if self.body2:
            self.content.body2.append(content)
        else:
            self.content.body.append(content)

    def handle_piece(self, piece, delimiter):
        token = self.parser.parse_token(piece)

        if delimiter == "":
            raise self.parser.exception(MProcEOFError)
        elif delimiter == "\n":
            self.content.expression = token
            self.parser.stack.append(SkipEmptyLinesContext(self.parser))
            self.reading_expression = False
        elif delimiter == "#":
            raise self.parser.exception_end(MProcStructureError)
        elif delimiter in "=)":
            self.wrong_delimiter(delimiter)
        elif delimiter == ",":
            self.create_list(token)
        elif delimiter == "(":
            self.create_call(token)
        elif delimiter in self.whitespace_set:
            self.skip_spaces(token)

    def handle_child_content(self, content, delimiter=None):
        if delimiter is None:
            if self.reading_expression:
                self.skip_spaces(content)
            else:
                self.append(content)
                self.parser.stack.append(SkipEmptyLinesContext(self.parser))
        elif delimiter == "":
            raise self.parser.exception(MProcEOFError)
        elif delimiter == "\n":
            self.content.expression = content
            self.parser.stack.append(SkipEmptyLinesContext(self.parser))
            self.reading_expression = False
        elif delimiter in "=)":
            self.wrong_delimiter(delimiter)
        elif delimiter == ",":
            self.create_list(content)
        elif delimiter == "(":
            self.create_call(content)


class BodySwitchFlowOperatorContext(Context):
    delimiters = set("\n") | {""}

    def __init__(self, content_type, name, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.content_type = content_type
        self.name = name

    def handle_piece(self, piece, delimiter):
        if piece:
            raise self.parser.exception(MProcParseError, piece)

        self.parser.stack.pop()
        nsc = self.parser.stack.pop()
        assert isinstance(nsc, NewStatementContext)  # should always be true in prod

        block_context = self.parser.stack[-1]
        if (not hasattr(block_context, "content") or
                not isinstance(block_context.content, self.content_type) or
                not hasattr(block_context, "body2") or
                block_context.body2):
            raise self.parser.exception(MProcParseError, "#" + self.name)

        block_context.body2 = True
        block_context.handle_child_content(None)

    def handle_child_content(self, content, delimiter=None):
        assert 0, "BodySwitchFlowOperatorContext may not have children"


class FunctionFlowOperatorContext(Context):
    def __init__(self, content, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.reading_definition = True
        self.content = content

    def read_statement(self):
        self.parser.stack.append(SkipEmptyLinesContext(self.parser))

    def append(self, token):
        self.content.body.append(token)

    def handle_piece(self, piece, delimiter):
        token = self.parser.parse_token(piece)

        if delimiter == "":
            raise self.parser.exception(MProcEOFError)

        elif delimiter == "\n":
            self.reading_definition = False
            self.content.definition = token
            self.read_statement()

        elif delimiter == "#":
            raise self.parser.exception_end(MProcStructureError)

        elif delimiter in "=)":
            self.wrong_delimiter(delimiter)

        elif delimiter == ",":
            self.create_list(token)

        elif delimiter == "(":
            self.create_call(token)

        elif delimiter in self.whitespace_set:
            self.skip_spaces(token)

    def handle_child_content(self, content, delimiter=None):
        if delimiter is None:
            if self.reading_definition:
                self.parser.stack.append(SearchForReturnContext(content, False, self.parser))
            else:
                self.append(content)
                self.read_statement()

        elif delimiter == "":
            raise self.parser.exception(MProcEOFError)

        elif delimiter == "\n":
            self.reading_definition = False
            self.content.definition = content
            self.read_statement()

        elif delimiter in "=)":
            self.wrong_delimiter(delimiter)

        elif delimiter == ",":
            self.create_list(content)

        elif delimiter == "(":
            self.create_call(content)


class SearchForReturnContext(SkipSpacesContext):
    delimiters = SkipSpacesContext.delimiters | {"-"}

    def handle_piece(self, piece, delimiter):
        if delimiter == "-":
            if piece:
                raise self.parser.exception(MProcParseError, piece)
            self.parser.stack.pop()
            self.parser.stack.append(MustBeArrowContext(self.token, self.parser))

        else:
            super().handle_piece(piece, delimiter)


class MustBeArrowContext(Context):
    exact_symbols = 1

    def __init__(self, content, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.content = content

    def handle_piece(self, piece, delimiter):
        if piece != ">":
            raise self.parser.exception(MProcParseError, "-" + piece)

        self.parser.stack.pop()
        self.parser.stack.append(FunctionDefinitionContext(self.content, self.parser))

    def handle_child_content(self, content, delimiter=None):
        assert 0, "MustBeArrowContext may not have children"


class FunctionDefinitionContext(Context):
    endl_as_whitespace = True

    def __init__(self, content, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.content = content

    def save_statement(self, token, delimiter=None):
        content = FunctionDefinition(self.content.line, self.content.symbol, self.content, token)
        super().save_statement(content, delimiter)

    def handle_piece(self, piece, delimiter):
        token = self.parser.parse_token(piece)

        if delimiter in "\n":  # empty too
            self.save_statement(token, delimiter)

        elif delimiter == "#":
            raise self.parser.exception_end(MProcStructureError)

        elif delimiter in "=)":
            self.wrong_delimiter(delimiter)

        elif delimiter == ",":
            self.create_list(token)

        elif delimiter == "(":
            self.create_call(token)

        elif delimiter in self.whitespace_set:
            self.skip_spaces(token)

    def handle_child_content(self, content, delimiter=None):
        if delimiter is None:
            self.skip_spaces(content)

        if delimiter in "\n":  # empty too
            self.save_statement(content, delimiter)

        elif delimiter in "=)":
            self.wrong_delimiter(delimiter)

        elif delimiter == ",":
            self.create_list(content)

        elif delimiter == "(":
            self.create_call(content)


class RawFunctionFlowOperatorContext(FunctionFlowOperatorContext):
    def read_statement(self):
        self.parser.stack.append(MLogContext(self.parser))

    def append(self, token):
        self.content.body += token


class MLogContext(Context):
    delimiters = {"#", ""}

    allow_spaces = False

    def handle_piece(self, piece, delimiter):
        if delimiter == "":
            raise self.parser.exception(MProcEOFError)

        if piece.rsplit("\n", 1)[-1].strip():
            raise self.parser.exception_end(MProcStructureError)

        self.parser.stack.pop()
        parent = self.parser.stack[-1]
        parent.append(piece)
        self.parser.stack.append(mlec := MLogEndContext(self.parser))
        mlec.handle_piece("", delimiter)

    def handle_child_content(self, content, delimiter=None):
        assert 0, "MLogContex may not have children"


class MLogEndContext(NewStatementContext):
    def handle_piece(self, piece, delimiter):
        assert delimiter == "#"
        self.parser.stack.append(BlockEndOnlyContext(self.parser))


class BlockEndOnlyContext(ExpectedFlowOperatorContext):
    def handle_piece(self, piece, delimiter):
        if piece not in self.block_end_operators:
            raise self.parser.exception(MProcParseError, "#" + piece)
        return super().handle_piece(piece, delimiter)


class ListContext(Context):
    """Context for parsing lists"""

    endl_as_whitespace = True

    def __init__(self, first, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.content = List(first.line, first.symbol, [first])

    def save_statement(self, token, delimiter=None):
        self.append(token)
        super().save_statement(self.content, delimiter)

    def skip_spaces(self, token, endl_as_whitespace=False):
        self.append(token)
        super().skip_spaces(None, endl_as_whitespace)

    def create_assignment(self, token):
        self.append(token)
        self.parser.stack.pop()
        super().create_assignment(self.content)

    def append(self, content):
        if content is not None:
            self.content.expressions.append(content)

    def handle_piece(self, piece, delimiter):
        token = self.parser.parse_token(piece) if piece else None
        if delimiter in "\n)":  # empty too
            self.save_statement(token, delimiter)

        elif delimiter in self.whitespace_set:
            self.skip_spaces(token)

        elif delimiter == ",":
            self.append(token)

        elif delimiter == "#":
            raise self.parser.exception_end(MProcStructureError)

        elif delimiter == "(":
            self.create_call(token)

        elif delimiter == "=":
            self.create_assignment(token)

    def handle_child_content(self, content, delimiter=None):
        if delimiter is None:
            self.skip_spaces(content)
        elif delimiter in ')':  # empty too
            self.save_statement(content, delimiter)

        elif delimiter == ",":
            self.append(content)

        elif delimiter == "(":
            self.create_call(content)

        elif delimiter == "=":
            self.create_assignment(content)

        elif delimiter == "\n":
            self.save_statement(content, delimiter)


class ArgumentListContext(ListContext):
    """Context for parsing list of arguments"""

    def create_assignment(self, token):
        self.parser.stack.append(NamedArgumentRightHandSideContext(token, self.parser))

    def append(self, content):
        if isinstance(content, List):
            self.content.expressions.extend(content.expressions)
        else:
            super().append(content)


class CallContext(Context):
    """Context for calling function/macros"""
    endl_as_whitespace = True

    def __init__(self, caller, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.caller = caller

    def save_statement(self, token, delimiter=None):
        content = Call(self.caller.line, self.caller.symbol, self.caller, token)
        super().save_statement(content, delimiter)

    def create_assignment(self, token):
        if token is None:
            raise self.parser.exception(MProcTokenExpectedError)
        self.parser.stack.append(NamedArgumentRightHandSideContext(token, self.parser))

    def create_list(self, token):
        if token is None:
            raise self.parser.exception(MProcTokenExpectedError)
        self.parser.stack.append(ArgumentListContext(token, self.parser))

    def handle_piece(self, piece, delimiter):
        token = self.parser.parse_token(piece) if piece else None
        if delimiter == ")":
            self.save_statement(token)

        elif delimiter in self.whitespace_set | {"\n"}:
            self.skip_spaces(token, True)

        elif delimiter == "#":
            raise self.parser.exception_end(MProcStructureError)

        elif delimiter == "=":
            self.create_assignment(token)

        elif delimiter == ",":
            self.create_list(token)

        elif delimiter == "(":
            self.create_call(token)

        elif delimiter == "":
            raise self.parser.exception(MProcEOFError)

    def handle_child_content(self, content, delimiter=None):
        if delimiter is None:
            self.skip_spaces(content, True)
        elif delimiter == ")":
            self.save_statement(content)

        elif delimiter == "#":
            raise self.parser.exception_end(MProcStructureError)

        elif delimiter == "\n":
            self.skip_spaces(content, True)

        elif delimiter == "=":
            self.create_assignment(content)

        elif delimiter == ",":
            self.create_list(content)

        elif delimiter == "(":
            self.create_call(content)

        elif delimiter == "":
            raise self.parser.exception(MProcEOFError)
