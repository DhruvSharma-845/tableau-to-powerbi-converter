"""
Parser for Tableau calculation formulas.

This module parses Tableau formula syntax into an AST-like structure
that can be used for translation to DAX.
"""

import re
from typing import Optional, List, Dict, Any, Tuple
from enum import Enum
from dataclasses import dataclass, field


class TokenType(Enum):
    """Token types for Tableau formula parsing."""
    # Literals
    NUMBER = "NUMBER"
    STRING = "STRING"
    BOOLEAN = "BOOLEAN"
    NULL = "NULL"
    
    # Identifiers
    FIELD = "FIELD"  # [Field Name]
    PARAMETER = "PARAMETER"  # [Parameter]
    
    # Operators
    PLUS = "PLUS"
    MINUS = "MINUS"
    MULTIPLY = "MULTIPLY"
    DIVIDE = "DIVIDE"
    POWER = "POWER"
    MODULO = "MODULO"
    
    # Comparison
    EQUALS = "EQUALS"
    NOT_EQUALS = "NOT_EQUALS"
    LESS_THAN = "LESS_THAN"
    GREATER_THAN = "GREATER_THAN"
    LESS_EQUAL = "LESS_EQUAL"
    GREATER_EQUAL = "GREATER_EQUAL"
    
    # Logical
    AND = "AND"
    OR = "OR"
    NOT = "NOT"
    
    # Keywords
    IF = "IF"
    THEN = "THEN"
    ELSE = "ELSE"
    ELSEIF = "ELSEIF"
    END = "END"
    CASE = "CASE"
    WHEN = "WHEN"
    
    # LOD Keywords
    FIXED = "FIXED"
    INCLUDE = "INCLUDE"
    EXCLUDE = "EXCLUDE"
    
    # Functions
    FUNCTION = "FUNCTION"
    
    # Punctuation
    LPAREN = "LPAREN"
    RPAREN = "RPAREN"
    LBRACKET = "LBRACKET"
    RBRACKET = "RBRACKET"
    LBRACE = "LBRACE"
    RBRACE = "RBRACE"
    COMMA = "COMMA"
    COLON = "COLON"
    
    # Special
    EOF = "EOF"
    UNKNOWN = "UNKNOWN"


@dataclass
class Token:
    """Represents a token in the formula."""
    type: TokenType
    value: Any
    position: int = 0


@dataclass
class ASTNode:
    """Base class for AST nodes."""
    node_type: str
    children: List['ASTNode'] = field(default_factory=list)
    value: Any = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class TableauFormulaParser:
    """
    Parser for Tableau calculation formulas.
    
    Converts Tableau formulas into an AST structure that can be
    analyzed and translated to DAX.
    """
    
    # Tableau functions categorized by type
    AGGREGATE_FUNCTIONS = {
        "SUM", "AVG", "MIN", "MAX", "COUNT", "COUNTD", "MEDIAN",
        "STDEV", "STDEVP", "VAR", "VARP", "CORR", "COVAR", "COVARP",
        "ATTR", "COLLECT",
    }
    
    TABLE_CALC_FUNCTIONS = {
        "RUNNING_SUM", "RUNNING_AVG", "RUNNING_COUNT", "RUNNING_MIN", "RUNNING_MAX",
        "WINDOW_SUM", "WINDOW_AVG", "WINDOW_COUNT", "WINDOW_MIN", "WINDOW_MAX",
        "WINDOW_MEDIAN", "WINDOW_STDEV", "WINDOW_STDEVP", "WINDOW_VAR", "WINDOW_VARP",
        "INDEX", "FIRST", "LAST", "SIZE",
        "LOOKUP", "PREVIOUS_VALUE",
        "RANK", "RANK_DENSE", "RANK_MODIFIED", "RANK_PERCENTILE", "RANK_UNIQUE",
        "TOTAL", "SCRIPT_BOOL", "SCRIPT_INT", "SCRIPT_REAL", "SCRIPT_STR",
    }
    
    STRING_FUNCTIONS = {
        "ASCII", "CHAR", "CONTAINS", "ENDSWITH", "STARTSWITH",
        "FIND", "FINDNTH", "LEFT", "RIGHT", "MID", "LEN", "LENGTH",
        "LOWER", "UPPER", "PROPER", "TRIM", "LTRIM", "RTRIM",
        "REPLACE", "SPACE", "SPLIT", "STR", "REGEXP_MATCH", "REGEXP_REPLACE",
        "REGEXP_EXTRACT", "REGEXP_EXTRACT_NTH",
    }
    
    DATE_FUNCTIONS = {
        "DATE", "DATETIME", "DATEADD", "DATEDIFF", "DATENAME", "DATEPART",
        "DATETRUNC", "DAY", "MONTH", "YEAR", "QUARTER", "WEEK",
        "WEEKDAY", "ISDATE", "MAKEDATE", "MAKEDATETIME", "MAKETIME",
        "NOW", "TODAY", "MAX", "MIN",
    }
    
    LOGICAL_FUNCTIONS = {
        "IF", "IIF", "IFNULL", "ZN", "ISNULL", "CASE",
        "ISDATE", "ISNUMBER", "ISSTRING",
    }
    
    TYPE_FUNCTIONS = {
        "INT", "FLOAT", "STR", "DATE", "DATETIME", "BOOL",
    }
    
    MATH_FUNCTIONS = {
        "ABS", "ACOS", "ASIN", "ATAN", "ATAN2", "COS", "COT", "SIN", "TAN",
        "CEILING", "FLOOR", "ROUND", "POWER", "SQRT", "SQUARE", "EXP", "LN", "LOG",
        "SIGN", "PI", "RADIANS", "DEGREES", "HEXBINX", "HEXBINY",
    }
    
    def __init__(self, formula: str):
        """
        Initialize parser with a formula string.
        
        Args:
            formula: Tableau calculation formula
        """
        self.formula = formula
        self.tokens: List[Token] = []
        self.position = 0
        self.current_token: Optional[Token] = None
    
    def parse(self) -> ASTNode:
        """
        Parse the formula and return an AST.
        
        Returns:
            ASTNode: Root of the abstract syntax tree
        """
        self.tokenize()
        self.position = 0
        self.current_token = self.tokens[0] if self.tokens else Token(TokenType.EOF, None)
        
        return self._parse_expression()
    
    def tokenize(self) -> List[Token]:
        """
        Tokenize the formula into a list of tokens.
        
        Returns:
            List[Token]: List of tokens
        """
        self.tokens = []
        pos = 0
        formula = self.formula
        
        while pos < len(formula):
            # Skip whitespace
            if formula[pos].isspace():
                pos += 1
                continue
            
            # String literals
            if formula[pos] in ('"', "'"):
                quote = formula[pos]
                end = pos + 1
                while end < len(formula) and formula[end] != quote:
                    if formula[end] == '\\':
                        end += 2
                    else:
                        end += 1
                end += 1
                self.tokens.append(Token(TokenType.STRING, formula[pos+1:end-1], pos))
                pos = end
                continue
            
            # Field references [Field Name]
            if formula[pos] == '[':
                end = formula.find(']', pos)
                if end != -1:
                    field_name = formula[pos+1:end]
                    self.tokens.append(Token(TokenType.FIELD, field_name, pos))
                    pos = end + 1
                    continue
            
            # LOD expressions {FIXED ...}
            if formula[pos] == '{':
                self.tokens.append(Token(TokenType.LBRACE, '{', pos))
                pos += 1
                continue
            
            if formula[pos] == '}':
                self.tokens.append(Token(TokenType.RBRACE, '}', pos))
                pos += 1
                continue
            
            # Numbers
            if formula[pos].isdigit() or (formula[pos] == '.' and pos + 1 < len(formula) and formula[pos + 1].isdigit()):
                end = pos
                has_dot = False
                while end < len(formula) and (formula[end].isdigit() or (formula[end] == '.' and not has_dot)):
                    if formula[end] == '.':
                        has_dot = True
                    end += 1
                self.tokens.append(Token(TokenType.NUMBER, float(formula[pos:end]), pos))
                pos = end
                continue
            
            # Operators and punctuation
            if formula[pos:pos+2] == '!=':
                self.tokens.append(Token(TokenType.NOT_EQUALS, '!=', pos))
                pos += 2
                continue
            if formula[pos:pos+2] == '<>':
                self.tokens.append(Token(TokenType.NOT_EQUALS, '<>', pos))
                pos += 2
                continue
            if formula[pos:pos+2] == '<=':
                self.tokens.append(Token(TokenType.LESS_EQUAL, '<=', pos))
                pos += 2
                continue
            if formula[pos:pos+2] == '>=':
                self.tokens.append(Token(TokenType.GREATER_EQUAL, '>=', pos))
                pos += 2
                continue
            
            single_char_tokens = {
                '+': TokenType.PLUS,
                '-': TokenType.MINUS,
                '*': TokenType.MULTIPLY,
                '/': TokenType.DIVIDE,
                '^': TokenType.POWER,
                '%': TokenType.MODULO,
                '=': TokenType.EQUALS,
                '<': TokenType.LESS_THAN,
                '>': TokenType.GREATER_THAN,
                '(': TokenType.LPAREN,
                ')': TokenType.RPAREN,
                ',': TokenType.COMMA,
                ':': TokenType.COLON,
            }
            
            if formula[pos] in single_char_tokens:
                self.tokens.append(Token(single_char_tokens[formula[pos]], formula[pos], pos))
                pos += 1
                continue
            
            # Keywords and identifiers
            if formula[pos].isalpha() or formula[pos] == '_':
                end = pos
                while end < len(formula) and (formula[end].isalnum() or formula[end] == '_'):
                    end += 1
                word = formula[pos:end].upper()
                
                # Check for keywords
                keyword_map = {
                    'IF': TokenType.IF,
                    'THEN': TokenType.THEN,
                    'ELSE': TokenType.ELSE,
                    'ELSEIF': TokenType.ELSEIF,
                    'END': TokenType.END,
                    'CASE': TokenType.CASE,
                    'WHEN': TokenType.WHEN,
                    'AND': TokenType.AND,
                    'OR': TokenType.OR,
                    'NOT': TokenType.NOT,
                    'FIXED': TokenType.FIXED,
                    'INCLUDE': TokenType.INCLUDE,
                    'EXCLUDE': TokenType.EXCLUDE,
                    'TRUE': TokenType.BOOLEAN,
                    'FALSE': TokenType.BOOLEAN,
                    'NULL': TokenType.NULL,
                }
                
                if word in keyword_map:
                    value = word
                    if word in ('TRUE', 'FALSE'):
                        value = word == 'TRUE'
                    self.tokens.append(Token(keyword_map[word], value, pos))
                else:
                    # It's a function or identifier
                    self.tokens.append(Token(TokenType.FUNCTION, formula[pos:end], pos))
                
                pos = end
                continue
            
            # Unknown character
            self.tokens.append(Token(TokenType.UNKNOWN, formula[pos], pos))
            pos += 1
        
        self.tokens.append(Token(TokenType.EOF, None, len(formula)))
        return self.tokens
    
    def _advance(self) -> Token:
        """Advance to the next token."""
        self.position += 1
        if self.position < len(self.tokens):
            self.current_token = self.tokens[self.position]
        else:
            self.current_token = Token(TokenType.EOF, None)
        return self.current_token
    
    def _parse_expression(self) -> ASTNode:
        """Parse an expression."""
        return self._parse_or()
    
    def _parse_or(self) -> ASTNode:
        """Parse OR expressions."""
        left = self._parse_and()
        
        while self.current_token.type == TokenType.OR:
            self._advance()
            right = self._parse_and()
            left = ASTNode(
                node_type="binary_op",
                children=[left, right],
                value="OR",
            )
        
        return left
    
    def _parse_and(self) -> ASTNode:
        """Parse AND expressions."""
        left = self._parse_not()
        
        while self.current_token.type == TokenType.AND:
            self._advance()
            right = self._parse_not()
            left = ASTNode(
                node_type="binary_op",
                children=[left, right],
                value="AND",
            )
        
        return left
    
    def _parse_not(self) -> ASTNode:
        """Parse NOT expressions."""
        if self.current_token.type == TokenType.NOT:
            self._advance()
            operand = self._parse_comparison()
            return ASTNode(
                node_type="unary_op",
                children=[operand],
                value="NOT",
            )
        
        return self._parse_comparison()
    
    def _parse_comparison(self) -> ASTNode:
        """Parse comparison expressions."""
        left = self._parse_additive()
        
        comparison_ops = {
            TokenType.EQUALS: "=",
            TokenType.NOT_EQUALS: "<>",
            TokenType.LESS_THAN: "<",
            TokenType.GREATER_THAN: ">",
            TokenType.LESS_EQUAL: "<=",
            TokenType.GREATER_EQUAL: ">=",
        }
        
        if self.current_token.type in comparison_ops:
            op = comparison_ops[self.current_token.type]
            self._advance()
            right = self._parse_additive()
            return ASTNode(
                node_type="comparison",
                children=[left, right],
                value=op,
            )
        
        return left
    
    def _parse_additive(self) -> ASTNode:
        """Parse additive expressions (+, -)."""
        left = self._parse_multiplicative()
        
        while self.current_token.type in (TokenType.PLUS, TokenType.MINUS):
            op = "+" if self.current_token.type == TokenType.PLUS else "-"
            self._advance()
            right = self._parse_multiplicative()
            left = ASTNode(
                node_type="binary_op",
                children=[left, right],
                value=op,
            )
        
        return left
    
    def _parse_multiplicative(self) -> ASTNode:
        """Parse multiplicative expressions (*, /, %)."""
        left = self._parse_power()
        
        while self.current_token.type in (TokenType.MULTIPLY, TokenType.DIVIDE, TokenType.MODULO):
            if self.current_token.type == TokenType.MULTIPLY:
                op = "*"
            elif self.current_token.type == TokenType.DIVIDE:
                op = "/"
            else:
                op = "%"
            self._advance()
            right = self._parse_power()
            left = ASTNode(
                node_type="binary_op",
                children=[left, right],
                value=op,
            )
        
        return left
    
    def _parse_power(self) -> ASTNode:
        """Parse power expressions (^)."""
        left = self._parse_unary()
        
        if self.current_token.type == TokenType.POWER:
            self._advance()
            right = self._parse_power()  # Right associative
            return ASTNode(
                node_type="binary_op",
                children=[left, right],
                value="^",
            )
        
        return left
    
    def _parse_unary(self) -> ASTNode:
        """Parse unary expressions (-value)."""
        if self.current_token.type == TokenType.MINUS:
            self._advance()
            operand = self._parse_unary()
            return ASTNode(
                node_type="unary_op",
                children=[operand],
                value="-",
            )
        
        return self._parse_primary()
    
    def _parse_primary(self) -> ASTNode:
        """Parse primary expressions (literals, fields, functions, etc.)."""
        token = self.current_token
        
        # Number literal
        if token.type == TokenType.NUMBER:
            self._advance()
            return ASTNode(node_type="number", value=token.value)
        
        # String literal
        if token.type == TokenType.STRING:
            self._advance()
            return ASTNode(node_type="string", value=token.value)
        
        # Boolean literal
        if token.type == TokenType.BOOLEAN:
            self._advance()
            return ASTNode(node_type="boolean", value=token.value)
        
        # Null literal
        if token.type == TokenType.NULL:
            self._advance()
            return ASTNode(node_type="null", value=None)
        
        # Field reference
        if token.type == TokenType.FIELD:
            self._advance()
            return ASTNode(node_type="field", value=token.value)
        
        # IF expression
        if token.type == TokenType.IF:
            return self._parse_if()
        
        # CASE expression
        if token.type == TokenType.CASE:
            return self._parse_case()
        
        # LOD expression
        if token.type == TokenType.LBRACE:
            return self._parse_lod()
        
        # Function call
        if token.type == TokenType.FUNCTION:
            return self._parse_function()
        
        # Parenthesized expression
        if token.type == TokenType.LPAREN:
            self._advance()
            expr = self._parse_expression()
            if self.current_token.type == TokenType.RPAREN:
                self._advance()
            return expr
        
        # Unknown - return an error node
        self._advance()
        return ASTNode(node_type="error", value=f"Unexpected token: {token.value}")
    
    def _parse_if(self) -> ASTNode:
        """Parse IF-THEN-ELSE expression."""
        self._advance()  # consume IF
        
        conditions = []
        results = []
        else_result = None
        
        # Parse first condition
        condition = self._parse_expression()
        conditions.append(condition)
        
        # Expect THEN
        if self.current_token.type == TokenType.THEN:
            self._advance()
        
        result = self._parse_expression()
        results.append(result)
        
        # Parse ELSEIF clauses
        while self.current_token.type == TokenType.ELSEIF:
            self._advance()
            condition = self._parse_expression()
            conditions.append(condition)
            
            if self.current_token.type == TokenType.THEN:
                self._advance()
            
            result = self._parse_expression()
            results.append(result)
        
        # Parse ELSE clause
        if self.current_token.type == TokenType.ELSE:
            self._advance()
            else_result = self._parse_expression()
        
        # Expect END
        if self.current_token.type == TokenType.END:
            self._advance()
        
        return ASTNode(
            node_type="if",
            children=conditions + results + ([else_result] if else_result else []),
            metadata={
                "conditions_count": len(conditions),
                "has_else": else_result is not None,
            }
        )
    
    def _parse_case(self) -> ASTNode:
        """Parse CASE-WHEN expression."""
        self._advance()  # consume CASE
        
        # Parse the expression to compare
        case_expr = self._parse_expression()
        
        when_values = []
        then_results = []
        else_result = None
        
        # Parse WHEN clauses
        while self.current_token.type == TokenType.WHEN:
            self._advance()
            when_value = self._parse_expression()
            when_values.append(when_value)
            
            if self.current_token.type == TokenType.THEN:
                self._advance()
            
            result = self._parse_expression()
            then_results.append(result)
        
        # Parse ELSE clause
        if self.current_token.type == TokenType.ELSE:
            self._advance()
            else_result = self._parse_expression()
        
        # Expect END
        if self.current_token.type == TokenType.END:
            self._advance()
        
        return ASTNode(
            node_type="case",
            children=[case_expr] + when_values + then_results + ([else_result] if else_result else []),
            metadata={
                "when_count": len(when_values),
                "has_else": else_result is not None,
            }
        )
    
    def _parse_lod(self) -> ASTNode:
        """Parse LOD expression {FIXED/INCLUDE/EXCLUDE [...] : expr}."""
        self._advance()  # consume {
        
        lod_type = None
        dimensions = []
        
        # Get LOD type
        if self.current_token.type in (TokenType.FIXED, TokenType.INCLUDE, TokenType.EXCLUDE):
            lod_type = self.current_token.value
            self._advance()
        
        # Parse dimensions
        while self.current_token.type == TokenType.FIELD:
            dimensions.append(self.current_token.value)
            self._advance()
            
            if self.current_token.type == TokenType.COMMA:
                self._advance()
        
        # Expect colon
        if self.current_token.type == TokenType.COLON:
            self._advance()
        
        # Parse the aggregation expression
        expression = self._parse_expression()
        
        # Expect }
        if self.current_token.type == TokenType.RBRACE:
            self._advance()
        
        return ASTNode(
            node_type="lod",
            children=[expression],
            value=lod_type,
            metadata={"dimensions": dimensions}
        )
    
    def _parse_function(self) -> ASTNode:
        """Parse function call."""
        func_name = self.current_token.value.upper()
        self._advance()  # consume function name
        
        arguments = []
        
        # Expect opening parenthesis
        if self.current_token.type == TokenType.LPAREN:
            self._advance()
            
            # Parse arguments
            if self.current_token.type != TokenType.RPAREN:
                arguments.append(self._parse_expression())
                
                while self.current_token.type == TokenType.COMMA:
                    self._advance()
                    arguments.append(self._parse_expression())
            
            # Expect closing parenthesis
            if self.current_token.type == TokenType.RPAREN:
                self._advance()
        
        # Determine function category
        category = self._categorize_function(func_name)
        
        return ASTNode(
            node_type="function",
            children=arguments,
            value=func_name,
            metadata={"category": category}
        )
    
    def _categorize_function(self, func_name: str) -> str:
        """Categorize a function by its type."""
        func_upper = func_name.upper()
        
        if func_upper in self.AGGREGATE_FUNCTIONS:
            return "aggregate"
        if func_upper in self.TABLE_CALC_FUNCTIONS:
            return "table_calc"
        if func_upper in self.STRING_FUNCTIONS:
            return "string"
        if func_upper in self.DATE_FUNCTIONS:
            return "date"
        if func_upper in self.LOGICAL_FUNCTIONS:
            return "logical"
        if func_upper in self.TYPE_FUNCTIONS:
            return "type"
        if func_upper in self.MATH_FUNCTIONS:
            return "math"
        
        return "unknown"
    
    def get_complexity_score(self, node: Optional[ASTNode] = None) -> int:
        """
        Calculate a complexity score for the formula.
        
        Higher scores indicate more complex formulas that may need
        more careful translation.
        
        Returns:
            int: Complexity score (0-100)
        """
        if node is None:
            node = self.parse()
        
        score = 0
        
        if node.node_type == "lod":
            score += 30  # LOD expressions are complex
            if len(node.metadata.get("dimensions", [])) > 2:
                score += 10  # Multiple dimensions add complexity
        
        if node.node_type == "function":
            category = node.metadata.get("category", "")
            if category == "table_calc":
                score += 40  # Table calculations are hardest
            elif category == "aggregate":
                score += 10
        
        if node.node_type == "if":
            score += 5
            if node.metadata.get("conditions_count", 0) > 2:
                score += 10
        
        if node.node_type == "case":
            score += 5
            if node.metadata.get("when_count", 0) > 3:
                score += 10
        
        # Recursively score children
        for child in node.children:
            if child:
                score += self.get_complexity_score(child) // 2
        
        return min(score, 100)
    
    def extract_fields(self, node: Optional[ASTNode] = None) -> List[str]:
        """Extract all field references from the formula."""
        if node is None:
            node = self.parse()
        
        fields = []
        
        if node.node_type == "field":
            fields.append(node.value)
        
        for child in node.children:
            if child:
                fields.extend(self.extract_fields(child))
        
        return list(set(fields))
    
    def extract_functions(self, node: Optional[ASTNode] = None) -> List[str]:
        """Extract all function calls from the formula."""
        if node is None:
            node = self.parse()
        
        functions = []
        
        if node.node_type == "function":
            functions.append(node.value)
        
        for child in node.children:
            if child:
                functions.extend(self.extract_functions(child))
        
        return functions
