from typing import Union

import libcst as cst
import libcst.matchers as m
from fixit import CstLintRule
from fixit import InvalidTestCase as Invalid
from fixit import ValidTestCase as Valid

INVALID_CAMEL_CASE_NAME: str = (
    "Class names should follow the [`CamelCase`]"
    + "(https://en.wikipedia.org/wiki/Camel_case) naming convention. "
    + "Please update the name of the class `{nodename}` accordingly. "
)

INVALID_SNAKE_CASE_NAME: str = (
    "Variable and function names should follow the [`snake_case`]"
    + "(https://en.wikipedia.org/wiki/Snake_case) naming convention. "
    + "Please update the name of the {nodetype} `{nodename}` accordingly. "
)


def _any_uppercase_letter(name: str) -> bool:
    """Check whether the given *name* contains any uppercase letter in it."""
    for letter in name:
        if letter.isupper():
            return True
    return False


class NamingConventionRule(CstLintRule):

    VALID = [
        Valid("type_hint: str"),
        Valid("type_hint_var: int = 5"),
        Valid("hello = 'world'"),
        Valid("snake_case = 'assign'"),
        Valid("for iteration in range(5): pass"),
        Valid("class SomeClass: pass"),
        Valid("class One: pass"),
        Valid("def oneword(): pass"),
        Valid("def some_extra_words(): pass"),
        Valid("all = names_are = valid_in_multiple_assign = 5"),
        Valid("(walrus := 'operator')"),
    ]

    INVALID = [
        Invalid("type_Hint_Var: int = 5"),
        Invalid("Hello = 'world'"),
        Invalid("ranDom_UpPercAse = 'testing'"),
        Invalid("for RandomCaps in range(5): pass"),
        Invalid("class lowerPascalCase: pass"),
        Invalid("class all_lower_case: pass"),
        Invalid("def oneWordInvalid(): pass"),
        Invalid("def Pascal_Case(): pass"),
        Invalid("valid = another_valid = Invalid = 5"),
        Invalid("(waLRus := 'operator')"),
        Invalid("def func(invalidParam, valid_param): pass"),
    ]

    def visit_ClassDef(self, node: cst.ClassDef) -> None:
        nodename = node.name.value
        if nodename[0].islower() or "_" in nodename:
            self.report(node, INVALID_CAMEL_CASE_NAME.format(nodename=nodename))

    def visit_AnnAssign(self, node: cst.AnnAssign) -> None:
        # The assignment target is optional, as it is possible to annotate an
        # expression without assigning to it: ``var: int``
        if node.value is not None:
            self._validate_snake_case_name(node, "variable")

    def visit_AssignTarget(self, node: cst.AssignTarget) -> None:
        self._validate_snake_case_name(node, "variable")

    def visit_For(self, node: cst.For) -> None:
        self._validate_snake_case_name(node, "variable")

    def visit_FunctionDef(self, node: cst.FunctionDef) -> None:
        self._validate_snake_case_name(node, "function")

    def visit_NamedExpr(self, node: cst.NamedExpr) -> None:
        self._validate_snake_case_name(node, "variable")

    def visit_Param(self, node: cst.Param) -> None:
        self._validate_snake_case_name(node, "parameter")

    def _validate_snake_case_name(
        self,
        node: Union[
            cst.AnnAssign,
            cst.AssignTarget,
            cst.For,
            cst.FunctionDef,
            cst.NamedExpr,
            cst.Param,
        ],
        nodetype: str,
    ) -> None:
        """Validate that the provided node conforms to the *snake_case* naming
        convention. The validation will be done for the following nodes:

        - ``cst.AnnAssign`` (Annotated assignment), which means an assignment which is
          type annotated like so ``var: int = 5``, to check the name of the variable.
        - ``cst.AssignTarget``, the target for the assignment, which is the left side
          part of the assignment expression. This can be a simple *Name* node or a
          sequence type node like *List* or *Tuple* in case of multiple assignments.
        - ``cst.For``, to check the target name of the iterator in the for statement.
        - ``cst.FunctionDef`` to check the name of the function.
        - ``cst.NamedExpr`` to check the assigned name in the expression. Also known
          as the walrus operator, this expression allows you to make an assignment
          inside an expression like so ``var := 10``.
        - ``cst.Param`` to check the name of the function parameters.
        """
        namekey: str = "nodename"
        extracted = m.extract(
            node,
            m.TypeOf(m.FunctionDef, m.Param)(
                name=m.Name(
                    value=m.SaveMatchedNode(
                        m.MatchIfTrue(_any_uppercase_letter), namekey
                    )
                )
            ),
        ) or m.extract(
            node,
            m.TypeOf(m.AnnAssign, m.AssignTarget, m.For, m.NamedExpr)(
                target=m.Name(
                    value=m.SaveMatchedNode(
                        m.MatchIfTrue(_any_uppercase_letter), namekey
                    )
                )
            ),
        )

        if extracted is not None:
            self.report(
                node,
                INVALID_SNAKE_CASE_NAME.format(
                    nodetype=nodetype, nodename=extracted[namekey]
                ),
            )