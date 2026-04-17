from __future__ import annotations

import ast


class CalculatorTool:
    name = "calculator"

    def run(self, user_input: str) -> str:
        expr = "".join(ch for ch in user_input if ch in "0123456789+-*/(). ")
        if not expr.strip():
            return "No numeric expression detected."

        try:
            node = ast.parse(expr, mode="eval")
        except SyntaxError:
            return "Could not parse arithmetic expression."

        allowed = (
            ast.Expression,
            ast.BinOp,
            ast.UnaryOp,
            ast.Add,
            ast.Sub,
            ast.Mult,
            ast.Div,
            ast.Mod,
            ast.Pow,
            ast.USub,
            ast.UAdd,
            ast.Constant,
        )
        if not all(isinstance(n, allowed) for n in ast.walk(node)):
            return "Expression contained unsupported operations."

        result = eval(compile(node, "<calculator>", "eval"), {"__builtins__": {}}, {})
        return f"{result}"
