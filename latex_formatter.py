from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Set


def format_sequence_as_latex(sequence: str) -> str:
    tokens = _rewrite_derivative_patterns(sequence.split())
    if not tokens:
        return ""
    return _LatexFormatter(tokens).parse()


def _rewrite_derivative_patterns(tokens: List[str]) -> List[str]:
    rewritten: List[str] = []
    i = 0
    while i < len(tokens):
        if (
            i + 3 < len(tokens)
            and tokens[i] == "d"
            and tokens[i + 1] == "/"
            and tokens[i + 2] == "d"
            and _is_simple_symbol(tokens[i + 3])
        ):
            rewritten.extend([r"\frac", "{", "d", "}", "{", f"d{tokens[i + 3]}", "}"])
            i += 4
            continue

        if (
            i + 4 < len(tokens)
            and tokens[i] == "d"
            and _is_simple_symbol(tokens[i + 1])
            and tokens[i + 2] == "/"
            and tokens[i + 3] == "d"
            and _is_simple_symbol(tokens[i + 4])
        ):
            rewritten.extend(
                [r"\frac", "{", f"d{tokens[i + 1]}", "}", "{", f"d{tokens[i + 4]}", "}"]
            )
            i += 5
            continue

        rewritten.append(tokens[i])
        i += 1

    return rewritten


def _is_simple_symbol(token: str) -> bool:
    if len(token) == 1 and token.isalnum():
        return True
    return token in {
        r"\alpha",
        r"\beta",
        r"\gamma",
        r"\theta",
        r"\lambda",
        r"\mu",
        r"\phi",
        r"\pi",
        r"\sigma",
        r"\Delta",
        r"\Pi",
        r"\infty",
    }


@dataclass
class _LatexFormatter:
    tokens: List[str]
    index: int = 0

    def parse(self, stop_tokens: Optional[Set[str]] = None) -> str:
        parts: List[str] = []
        stop_tokens = stop_tokens or set()

        while self.index < len(self.tokens) and self.tokens[self.index] not in stop_tokens:
            parts.append(self._parse_item())

        return _join_math(parts)

    def _parse_item(self) -> str:
        atom = self._parse_atom()

        while self.index < len(self.tokens) and self.tokens[self.index] in {r"\limits", "_", "^"}:
            marker = self.tokens[self.index]
            self.index += 1
            if marker == r"\limits":
                atom += marker
                continue
            atom += f"{marker}{self._parse_required_group()}"

        return atom

    def _parse_atom(self) -> str:
        token = self.tokens[self.index]

        if token == "{":
            self.index += 1
            inner = self.parse(stop_tokens={"}"})
            if self.index < len(self.tokens) and self.tokens[self.index] == "}":
                self.index += 1
            return "{" + inner + "}"

        if token == "[":
            self.index += 1
            inner = self.parse(stop_tokens={"]"})
            if self.index < len(self.tokens) and self.tokens[self.index] == "]":
                self.index += 1
            return "[" + inner + "]"

        self.index += 1

        if token == r"\frac":
            numerator = self._parse_required_group()
            denominator = self._parse_required_group()
            return f"{token}{numerator}{denominator}"

        if token == r"\sqrt":
            return f"{token}{self._parse_required_group()}"

        return token

    def _parse_required_group(self) -> str:
        if self.index >= len(self.tokens):
            return "{}"
        if self.tokens[self.index] == "{":
            return self._parse_atom()
        return "{" + self._parse_item() + "}"


def _join_math(parts: List[str]) -> str:
    result = ""
    for part in parts:
        if not result:
            result = part
            continue
        if _needs_space(result, part):
            result += " "
        result += part
    return result


def _needs_space(previous: str, current: str) -> bool:
    no_space_after = ("{", "[", "(", "/", "^", "_")
    no_space_before = ("}", "]", ")", ",", ".", ";", ":", "/", "^", "_")

    if previous.endswith(no_space_after):
        return False
    if current.startswith(no_space_before):
        return False
    if current.startswith(r"\limits"):
        return False
    return True
