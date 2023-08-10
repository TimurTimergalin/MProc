from mproc.parser import Parser
from mproc.syntax_tree import *
import pprint
from sys import stderr


def test1():
    name = "src/empty.mproc"

    tree = Parser(name).run()

    match tree:
        case Root(body=[]):
            pass
        case _:
            pprint.pprint(tree, stderr)
            assert 0


def test2():
    name = "src/simple.mproc"

    tree = Parser(name).run()

    match tree:
        case Root(body=[
            Assignment(lhs=Token(name="a"), rhs=List(expressions=[NumericLiteral(value=2), NumericLiteral(value=3)])),
            Assignment(lhs=List(expressions=[Token(name="b"), Token(name="c")]), rhs=List(expressions=[
                Token(name="d"),
                Call(called=Token(name="f"), arguments=StringLiteral(value="123"))
            ])),
            Call(called=Token(name="f"),
                 arguments=List(expressions=[NumericLiteral(value=48), NumericLiteral(value=97)]))
        ]):
            pass
        case _:
            pprint.pprint(tree, stderr)
            assert 0


def test3():
    name = "src/blocks.mproc"

    tree = Parser(name).run()

    match tree:
        case Root(body=[
            Init(body=[
                Assignment(lhs=Token(name="a"), rhs=NumericLiteral(value=3)),
                Assignment(lhs=Token(name="b"), rhs=NumericLiteral(value=4)),
                Final(expression=Assignment(lhs=Token(name="c"), rhs=NumericLiteral(value=4)))
            ]),
            Def(body=[
                Token(name="message1")
            ]),
            Prog(body=[
                Call(called=Token(name="print"), arguments=Token(name="a")),
                Call(called=Token(name="print"), arguments=Token(name="b")),
                Call(called=Token(name="print"), arguments=Token(name="c")),
                Call(called=Token(name="printflush"), arguments=Token(name="message1"))
            ])
        ]):
            pass
        case _:
            pprint.pprint(tree, stderr)
            assert 0


def test4():
    name = "src/functions.mproc"

    tree = Parser(name).run()

    match tree:
        case Root(body=[
            Func(
                definition=FunctionDefinition(
                    call=Call(
                        called=Token(name="func"),
                        arguments=List(expressions=[Token(name="a"), Token(name="b")])
                    )
                ),
                body=[
                    Return(expression=List(expressions=[
                        Call(
                            called=Token(name="add"),
                            arguments=List(expressions=[Token(name="a"), Token(name="b")])
                        ),
                        Call(
                            called=Token(name="pow"),
                            arguments=List(expressions=[Token(name="b"), Token(name="a")])
                        )
                    ]))
                ]
            ),
            Func(
                definition=Call(
                    called=Token(name="proc"),
                    arguments=List(expressions=[Token(name="a"), Token(name="e")])
                ),
                body=[
                    Assignment(
                        lhs=Token(name="global_result"),
                        rhs=Call(
                            called=Token(name="add"),
                            arguments=List(expressions=[
                                Call(
                                    called=Token(name="sub"),
                                    arguments=List(expressions=[
                                        Token(name="a"),
                                        Call(
                                            called=Token(name="pow"),
                                            arguments=List(expressions=[Token(name="e"), Token(name="e")])
                                        )
                                    ])
                                ),
                                Call(
                                    called=Token(name="flip"),
                                    arguments=Token(name="a")
                                )
                            ])
                        )
                    ),
                    Return(expression=Token(name="true"))
                ]
            )
        ]):
            pass
        case _:
            pprint.pprint(tree, stderr)
            assert 0


def test5():
    name = "src/raw.mproc"

    tree = Parser(name).run()

    match tree:
        case Root(body=[
            MLog(
                body="set result 2\n"
                     "sensor result block1 @copper  \n"
                     "jump -1 always 0 0\n"
            ),
            RawFunc(
                definition=FunctionDefinition(
                    call=Call(
                        called=Token(name="raw_func"),
                        arguments=List(expressions=[Token(name="inp1"), Token(name="inp2")])
                    ),
                    returns=List(expressions=[Token(name="out1"), Token(name="out2"), Token(name="out3")])
                ),
                body="op add {out1} {inp1} {inp2}\n"
                     "op sub {out2} {inp2} {inp1}\n"
                     "op mul {out3} {inp1} {inp1}\n"
                     "set @counter 48\n"
            )
        ]):
            pass
        case _:
            pprint.pprint(tree, stderr)
            assert 0


def test6():
    name = "src/conditions.mproc"

    tree = Parser(name).run()

    match tree:
        case Root(body=[
            Prog(body=[
                If(
                    expression=Call(
                        called=Token(name="lessThan"),
                        arguments=List(expressions=[Token(name="a"), NumericLiteral(value=3)])
                    ),
                    body=[
                        If(
                            expression=Call(
                                called=Token(name="lessThan"),
                                arguments=List(expressions=[Token(name="a"), NumericLiteral(value=2)])
                            ),
                            body=[
                                Call(
                                    called=Token(name="print"),
                                    arguments=StringLiteral(value="small\\n")
                                )
                            ],
                            body2=[
                                Call(
                                    # called=Token(name="print"),
                                    arguments=StringLiteral(value='medium\\n')
                                )
                            ]
                        )
                    ],
                    body2=[
                        Call(
                            called=Token(name="print"),
                            arguments=StringLiteral(value="large\\n")
                        ),
                        Loop(
                            expression=Call(
                                called=Token(name="greaterThanEq"),
                                arguments=List(expressions=[Token(name="a"), NumericLiteral(value=3)])
                            ),
                            body=[
                                Call(
                                    called=Token(name="print"),
                                    arguments=StringLiteral(value="making smaller!\\n")
                                )
                            ],
                            body2=[
                                Assignment(
                                    lhs=Token(name="a"),
                                    rhs=Call(
                                        called=Token(name="sub"),
                                        arguments=List(expressions=[Token(name="a"), NumericLiteral(value=1)])
                                    )
                                )
                            ]
                        )
                    ]
                ),
                Call(
                    called=Token(name="print"),
                    arguments=Token(name="a")
                )
            ])
        ]):
            pass
        case _:
            pprint.pprint(tree, stderr)
            assert 0


if __name__ == '__main__':
    i = 1
    while (test := globals().get(f"test{i}")) is not None:
        test()
        print(f"{test.__name__}: Ok")
        i += 1
