"""
OCI policy statement parser using ANTLR. Requires generated parser in grammar/gen/.
Run: ./scripts/generate_parser.sh  (needs Java)
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

try:
    from antlr4 import InputStream, CommonTokenStream
    from antlr4.error.ErrorListener import ErrorListener
    from grammar.gen.grammar.OciPolicyLexer import OciPolicyLexer
    from grammar.gen.grammar.OciPolicyParser import OciPolicyParser
    from grammar.gen.grammar.OciPolicyVisitor import OciPolicyVisitor
except ImportError as e:
    raise ImportError(
        "ANTLR-generated parser not found. Run from project root:\n  ./scripts/generate_parser.sh\n"
        "(Requires Java and antlr4-tools in env.)"
    ) from e

logger = logging.getLogger(__name__)


@dataclass
class ParseLogEntry:
    """Single entry in the parse log (one error or one success)."""
    line_num: Optional[int] = None   # 1-based line in statements file (for context)
    input_snippet: str = ""          # first N chars of the statement
    stage: str = ""                  # "lexer" | "parser" | "visit" | "ok"
    line: int = 0                    # ANTLR line (1-based)
    column: int = 0                  # ANTLR column (0-based)
    message: str = ""
    offending_text: str = ""         # offending token/symbol if any
    success: bool = False
    result_summary: str = ""          # e.g. "effect=Allow, subject=group, ..."
    # Where-in-process debugging (for failures)
    where_in_process: str = ""       # e.g. "Lexer → tokenization" or "Parser → conditionExpr"
    parser_rule_stack: Optional[list[str]] = None  # rule invocation stack when parser failed
    expected_tokens: str = ""         # expected token names when parser failed


def _format_where_in_process(stage: str, rule_stack: list[str] | None, expected: str) -> str:
    """Build a single-line 'where failed' description for the log."""
    if stage == "lexer":
        return "Lexer → tokenization (unrecognized character or sequence)"
    if stage == "parser":
        parts = ["Parser"]
        if rule_stack:
            parts.append(" → ")
            parts.append(" → ".join(reversed(rule_stack)))
        else:
            parts.append(" (syntax)")
        if expected:
            parts.append(f" [expected one of: {expected}]")
        return "".join(parts)
    if stage == "visit":
        return "Visitor → building result (visit returned None)"
    return stage


class CollectingErrorListener(ErrorListener):
    """Collects lexer/parser errors for logging instead of printing to stderr."""

    def __init__(self, log: list[ParseLogEntry], stage: str):
        self.log = log
        self.stage = stage

    def syntaxError(self, recognizer, offendingSymbol, line, column, msg, e):
        offending_text = ""
        if offendingSymbol is not None and hasattr(offendingSymbol, "text"):
            offending_text = getattr(offendingSymbol, "text", str(offendingSymbol))

        rule_stack: list[str] = []
        expected_str = ""
        if self.stage == "parser" and recognizer is not None and e is not None:
            try:
                rule_stack = list(recognizer.getRuleInvocationStack())
            except Exception:
                pass
            try:
                expected = e.getExpectedTokens()
                if expected is not None and hasattr(recognizer, "symbolicNames"):
                    names = recognizer.symbolicNames or []
                    tokens = []
                    for tok_type in expected:
                        if 0 <= tok_type < len(names) and names[tok_type] != "<INVALID>":
                            tokens.append(names[tok_type])
                    expected_str = ", ".join(sorted(set(tokens))[:15])
                    if len(set(tokens)) > 15:
                        expected_str += ", ..."
            except Exception:
                pass

        where = _format_where_in_process(self.stage, rule_stack or None, expected_str)
        self.log.append(ParseLogEntry(
            stage=self.stage,
            line=line,
            column=column,
            message=msg,
            offending_text=offending_text,
            success=False,
            where_in_process=where,
            parser_rule_stack=rule_stack if rule_stack else None,
            expected_tokens=expected_str,
        ))


class ToDictVisitor(OciPolicyVisitor):
    """Builds the same dict structure as the original tokenize_statement()."""

    def visitPolicyStatement(self, ctx: OciPolicyParser.PolicyStatementContext):
        if ctx.defineStatement():
            return self.visit(ctx.defineStatement())
        return self.visit(ctx.accessStatement())

    def visitDefineStatement(self, ctx: OciPolicyParser.DefineStatementContext):
        define_type = self._definable_type(ctx.definableType())
        alias = ctx.alias.getText() if ctx.alias else ""
        value = ctx.value.getText() if ctx.value else ""
        return {
            "statement_type": "define",
            "define_type": define_type,
            "alias": alias,
            "value": value,
        }

    def _definable_type(self, ctx):
        if ctx is None:
            return ""
        return ctx.getText().lower()

    def visitAccessStatement(self, ctx: OciPolicyParser.AccessStatementContext):
        out = {}
        if ctx.effect():
            out["effect"] = ctx.effect().getText()
        if ctx.subject():
            out["subject"] = ctx.subject().getText()
        if ctx.principalSpec():
            spec = ctx.principalSpec()
            if spec.principalList() is not None:
                id_list = spec.principalList().identifier()
                principals = [c.getText() for c in (id_list if isinstance(id_list, list) else [id_list])]
                out["principals"] = principals
            elif spec.principalOcid is not None:
                out["principal_type"] = "ocid"
                out["principals"] = [spec.principalOcid.getText()]
        if ctx.verb():
            out["verb"] = ctx.verb().getText()
        if ctx.resource() and ctx.resource().resourceId():
            out["resource"] = ctx.resource().resourceId().getText()
        if ctx.location():
            loc = ctx.location()
            if loc.TENANCY():
                out["location_type"] = "tenancy"
                out["compartment"] = "tenancy"
            elif loc.ANY_TENANCY():
                out["location_type"] = "any-tenancy"
                out["compartment"] = "any-tenancy"
            elif loc.COMPARTMENT() and loc.compartmentPath():
                out["location_type"] = "compartment"
                path_parts = [c.getText() for c in loc.compartmentPath().identifier()]
                out["compartment"] = ":".join(path_parts)
        if ctx.whereClause() and ctx.whereClause().condition():
            self._add_condition(out, ctx.whereClause().condition())
        return out

    def _add_condition(self, out, cond_ctx):
        if cond_ctx.conditionList() is not None:
            if cond_ctx.ALL():
                out["condition_selector"] = "all"
            else:
                out["condition_selector"] = "any"
            exprs = cond_ctx.conditionList().conditionExpr()
            if isinstance(exprs, list):
                out["condition"] = ",".join(e.getText() for e in exprs)
            else:
                out["condition"] = exprs.getText()
        elif cond_ctx.singleCondition():
            out["condition"] = cond_ctx.singleCondition().getText()

    def visitIdentifier(self, ctx: OciPolicyParser.IdentifierContext):
        return ctx.getText()

    def visitOcid(self, ctx: OciPolicyParser.OcidContext):
        return ctx.getText()


def parse_statement(
    statement: str,
    log: Optional[list[ParseLogEntry]] = None,
    line_num: Optional[int] = None,
    input_snippet_max_len: int = 60,
) -> dict:
    """
    Parse a single OCI policy statement and return a dict compatible with
    the previous tokenize_statement() output. If log is provided, append
    ParseLogEntry items for errors (and one success entry if parsing succeeded).
    """
    statement = statement.strip()
    if not statement:
        return {}

    snippet = statement[:input_snippet_max_len] + ("..." if len(statement) > input_snippet_max_len else "")
    log_entries: list[ParseLogEntry] = log if log is not None else []

    input_stream = InputStream(statement)
    lexer = OciPolicyLexer(input_stream)
    stream = CommonTokenStream(lexer)

    if log is not None:
        lexer.removeErrorListeners()
        lexer.addErrorListener(CollectingErrorListener(log_entries, "lexer"))

    parser = OciPolicyParser(stream)
    if log is not None:
        parser.removeErrorListeners()
        parser.addErrorListener(CollectingErrorListener(log_entries, "parser"))

    tree = parser.policyStatement()
    num_errors = parser.getNumberOfSyntaxErrors()

    def _fill_log_context():
        for e in log_entries:
            if e.line_num is None:
                e.line_num = line_num
            if e.input_snippet == "":
                e.input_snippet = snippet

    if num_errors > 0:
        _fill_log_context()
        return {"statement_type": "error", "raw": statement}

    visitor = ToDictVisitor()
    result = visitor.visit(tree)
    if result is None:
        if log is not None:
            log_entries.append(ParseLogEntry(
                line_num=line_num,
                input_snippet=snippet,
                stage="visit",
                message="Visitor returned None",
                success=False,
                where_in_process="Visitor → building result (visit returned None)",
            ))
        return {"statement_type": "error", "raw": statement}

    if log is not None:
        summary = ", ".join(f"{k}={v!r}" for k, v in result.items() if not k.startswith("_"))
        log_entries.append(ParseLogEntry(
            line_num=line_num,
            input_snippet=snippet,
            stage="ok",
            message="Parsed successfully",
            success=True,
            result_summary=summary[:200],
        ))
        _fill_log_context()
    return result


def parse_statement_with_log(
    statement: str,
    line_num: Optional[int] = None,
) -> tuple[dict, list[ParseLogEntry]]:
    """Parse a statement and return (result_dict, list of log entries for this statement)."""
    log: list[ParseLogEntry] = []
    result = parse_statement(statement, log=log, line_num=line_num)
    for e in log:
        e.line_num = line_num
        if not e.input_snippet:
            e.input_snippet = statement[:60] + ("..." if len(statement) > 60 else "")
    return result, log


def tokenize_statement(statement: str) -> dict:
    """Alias for parse_statement for drop-in replacement of modules.lexer.tokenize_statement."""
    return parse_statement(statement)


def write_parse_log(entries: list[ParseLogEntry], path: str | None = None) -> str:
    """Format log entries and write to path. Returns the formatted string."""
    lines = []
    lines.append("=" * 80)
    lines.append("OCI Policy statement parse log")
    lines.append("=" * 80)

    errors = [e for e in entries if not e.success]
    if errors:
        lines.append("")
        lines.append("--- SUMMARY: ERRORS (with where failed) ---")
        for e in errors:
            lines.append(f"  Line {e.line_num}: [{e.stage}] {e.message!s}")
            lines.append(f"    Where failed: {e.where_in_process or _format_where_in_process(e.stage, e.parser_rule_stack, e.expected_tokens)}")
            if e.parser_rule_stack:
                lines.append(f"    Parser rule stack: {' → '.join(e.parser_rule_stack)}")
            if e.expected_tokens:
                lines.append(f"    Expected tokens: {e.expected_tokens}")
            if e.offending_text:
                lines.append(f"    Offending: {e.offending_text!r}")
            lines.append(f"    Snippet: {e.input_snippet!r}")
        lines.append("")

    lines.append("--- ALL ENTRIES (in order) ---")
    for i, e in enumerate(entries):
        lines.append("")
        lines.append(f"--- Entry {i + 1} ---")
        if e.line_num is not None:
            lines.append(f"  Statement line #: {e.line_num}")
        lines.append(f"  Input snippet: {e.input_snippet!r}")
        lines.append(f"  Stage: {e.stage}")
        if not e.success and e.where_in_process:
            lines.append(f"  Where failed: {e.where_in_process}")
        if e.parser_rule_stack:
            lines.append(f"  Parser rule stack: {' → '.join(e.parser_rule_stack)}")
        if e.expected_tokens:
            lines.append(f"  Expected tokens: {e.expected_tokens}")
        if e.line or e.column or e.message:
            lines.append(f"  Position: line {e.line}, column {e.column}")
            lines.append(f"  Message: {e.message}")
        if e.offending_text:
            lines.append(f"  Offending text: {e.offending_text!r}")
        lines.append(f"  Success: {e.success}")
        if e.result_summary:
            lines.append(f"  Result: {e.result_summary}")
    text = "\n".join(lines)
    if path:
        with open(path, "w") as f:
            f.write(text)
    return text
