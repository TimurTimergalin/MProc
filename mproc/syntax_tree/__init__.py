from dataclasses import dataclass


@dataclass
class SyntaxTreeNode:
    line: int
    symbol: int


@dataclass
class Root(SyntaxTreeNode):
    """Represents the whole file"""

    body: list


@dataclass
class Assignment(SyntaxTreeNode):
    """Represents "=" statement/expression"""
    lhs: object
    rhs: object


@dataclass
class Break(SyntaxTreeNode):
    """Represents #break statement"""


@dataclass
class Call(SyntaxTreeNode):
    """Represents function call expression"""
    called: object
    arguments: object


@dataclass
class Continue(SyntaxTreeNode):
    """Represents #continue statement"""


@dataclass
class Def(SyntaxTreeNode):
    """Represents #def block"""

    body: list


@dataclass
class Link(SyntaxTreeNode):
    """Represents #link block"""

    body: list


@dataclass
class End(SyntaxTreeNode):
    """Represents #end statement"""


@dataclass
class FunctionDefinition(SyntaxTreeNode):
    """Represents a function definition with returns"""

    call: object
    returns: object


@dataclass
class If(SyntaxTreeNode):
    """Represents #if block"""

    expression: object
    body: list
    body2: list


@dataclass
class Import(SyntaxTreeNode):
    """Represents #import statement"""

    expression: object


@dataclass
class Init(SyntaxTreeNode):
    """Represents #init block"""

    body: list


@dataclass
class List(SyntaxTreeNode):
    """Represents list of expressions separated with a comma"""

    expressions: list


@dataclass
class Loop(SyntaxTreeNode):
    """Represents #loop block"""

    expression: object
    body: list
    body2: list


@dataclass
class NumericLiteral(SyntaxTreeNode):
    """Represents numeric literal"""

    value: int | float


@dataclass
class Func(SyntaxTreeNode):
    """Represents #func block"""

    definition: object
    body: list


@dataclass
class Prog(SyntaxTreeNode):
    """Represents #prog block"""

    body: list


@dataclass
class Return(SyntaxTreeNode):
    """Represents #return statement"""
    expression: object


@dataclass
class Stop(SyntaxTreeNode):
    """Represents #stop statement"""


@dataclass
class StringLiteral(SyntaxTreeNode):
    """Represents string literal"""

    value: str


@dataclass
class Token(SyntaxTreeNode):
    """Represents a name of a variable/function/namespace/enum/etc"""

    name: str


@dataclass
class Wait(SyntaxTreeNode):
    """Represents #stop statement"""

    expression: object


@dataclass
class RawFunc(SyntaxTreeNode):
    """Represents #rawfunc block"""
    definition: object
    body: str


@dataclass
class MLog(SyntaxTreeNode):
    """Represents #mlog block"""
    body: str


@dataclass
class Enum(SyntaxTreeNode):
    """Represents #enum block"""
    definition: object
    body: list


@dataclass
class Using(SyntaxTreeNode):
    """Represents #using block"""
    expression: object


@dataclass
class Var(SyntaxTreeNode):
    """Represents #var block"""
    expression: object
