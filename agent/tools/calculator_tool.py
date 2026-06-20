"""计算器工具：安全执行数值表达式。"""

import ast
import operator
from typing import Any

from agent.tools.base import BaseTool, ToolResult


# 允许的二元运算符
_BIN_OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Pow: operator.pow,
    ast.Mod: operator.mod,
    ast.FloorDiv: operator.floordiv,
}

# 允许的一元运算符
_UNARY_OPS = {
    ast.UAdd: operator.pos,
    ast.USub: operator.neg,
}


class CalculatorTool(BaseTool):
    """安全计算数值表达式，支持 + - * / // % ** 和括号。"""

    name = "calculator"
    description = "安全计算数值表达式，例如 '(2 + 3) * 4' 或 '10 ** 3'。"
    input_schema = {
        "type": "object",
        "properties": {
            "expression": {
                "type": "string",
                "description": "要计算的数学表达式",
            },
        },
        "required": ["expression"],
    }

    def run(self, expression: str) -> ToolResult:
        try:
            value = self._safe_eval(expression)
            return ToolResult(success=True, data={"expression": expression, "result": value})
        except Exception as exc:
            return ToolResult(success=False, error=str(exc))

    def _safe_eval(self, expression: str) -> Any:
        """仅允许数值运算的 AST 求值。"""
        tree = ast.parse(expression.strip(), mode="eval")
        return self._eval_node(tree.body)

    def _eval_node(self, node: ast.AST) -> Any:
        if isinstance(node, ast.Num):  # Python < 3.8
            return node.n
        if isinstance(node, ast.Constant):  # Python >= 3.8
            if isinstance(node.value, (int, float)):
                return node.value
            raise ValueError("Only numeric constants are allowed")
        if isinstance(node, ast.BinOp):
            op_type = type(node.op)
            if op_type not in _BIN_OPS:
                raise ValueError(f"Unsupported binary operator: {op_type.__name__}")
            left = self._eval_node(node.left)
            right = self._eval_node(node.right)
            return _BIN_OPS[op_type](left, right)
        if isinstance(node, ast.UnaryOp):
            op_type = type(node.op)
            if op_type not in _UNARY_OPS:
                raise ValueError(f"Unsupported unary operator: {op_type.__name__}")
            operand = self._eval_node(node.operand)
            return _UNARY_OPS[op_type](operand)
        if isinstance(node, ast.Expression):
            return self._eval_node(node.body)
        if isinstance(node, ast.Call):
            raise ValueError("Function calls are not allowed")
        if isinstance(node, ast.Name):
            raise ValueError("Variables are not allowed")
        raise ValueError(f"Unsupported expression node: {type(node).__name__}")
