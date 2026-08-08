# Generated from grammar/OciPolicy.g4 by ANTLR 4.13.2
# encoding: utf-8
from antlr4 import *
from io import StringIO
import sys
if sys.version_info[1] > 5:
	from typing import TextIO
else:
	from typing.io import TextIO

def serializedATN():
    return [
        4,1,38,185,2,0,7,0,2,1,7,1,2,2,7,2,2,3,7,3,2,4,7,4,2,5,7,5,2,6,7,
        6,2,7,7,7,2,8,7,8,2,9,7,9,2,10,7,10,2,11,7,11,2,12,7,12,2,13,7,13,
        2,14,7,14,2,15,7,15,2,16,7,16,2,17,7,17,2,18,7,18,2,19,7,19,2,20,
        7,20,2,21,7,21,1,0,1,0,3,0,47,8,0,1,1,1,1,1,1,1,1,1,1,1,1,1,2,1,
        2,1,3,1,3,1,3,3,3,60,8,3,1,3,1,3,1,3,1,3,1,3,1,3,3,3,68,8,3,1,4,
        1,4,1,5,1,5,1,6,1,6,1,6,3,6,77,8,6,1,7,1,7,1,7,5,7,82,8,7,10,7,12,
        7,85,9,7,1,8,1,8,1,9,1,9,1,10,1,10,1,11,1,11,1,11,1,11,3,11,97,8,
        11,1,12,1,12,1,12,5,12,102,8,12,10,12,12,12,105,9,12,1,13,1,13,1,
        13,1,14,1,14,1,14,1,14,1,14,1,14,1,14,1,14,1,14,1,14,1,14,3,14,121,
        8,14,1,15,1,15,1,15,5,15,126,8,15,10,15,12,15,129,9,15,1,16,1,16,
        1,16,1,16,3,16,135,8,16,1,16,1,16,1,16,1,16,3,16,141,8,16,1,16,1,
        16,1,16,1,16,1,16,1,16,3,16,149,8,16,1,17,1,17,1,17,5,17,154,8,17,
        10,17,12,17,157,9,17,1,18,1,18,1,19,1,19,1,19,1,19,3,19,165,8,19,
        1,19,1,19,1,19,1,19,3,19,171,8,19,1,19,1,19,1,19,1,19,1,19,1,19,
        3,19,179,8,19,1,20,1,20,1,21,1,21,1,21,0,0,22,0,2,4,6,8,10,12,14,
        16,18,20,22,24,26,28,30,32,34,36,38,40,42,0,6,2,0,6,7,12,12,1,0,
        1,4,1,0,6,9,1,0,19,22,1,0,32,33,3,0,6,6,18,18,32,32,184,0,46,1,0,
        0,0,2,48,1,0,0,0,4,54,1,0,0,0,6,56,1,0,0,0,8,69,1,0,0,0,10,71,1,
        0,0,0,12,76,1,0,0,0,14,78,1,0,0,0,16,86,1,0,0,0,18,88,1,0,0,0,20,
        90,1,0,0,0,22,96,1,0,0,0,24,98,1,0,0,0,26,106,1,0,0,0,28,120,1,0,
        0,0,30,122,1,0,0,0,32,148,1,0,0,0,34,150,1,0,0,0,36,158,1,0,0,0,
        38,178,1,0,0,0,40,180,1,0,0,0,42,182,1,0,0,0,44,47,3,2,1,0,45,47,
        3,6,3,0,46,44,1,0,0,0,46,45,1,0,0,0,47,1,1,0,0,0,48,49,5,5,0,0,49,
        50,3,4,2,0,50,51,3,40,20,0,51,52,5,17,0,0,52,53,3,42,21,0,53,3,1,
        0,0,0,54,55,7,0,0,0,55,5,1,0,0,0,56,57,3,8,4,0,57,59,3,10,5,0,58,
        60,3,12,6,0,59,58,1,0,0,0,59,60,1,0,0,0,60,61,1,0,0,0,61,62,5,10,
        0,0,62,63,3,16,8,0,63,64,3,18,9,0,64,65,5,11,0,0,65,67,3,22,11,0,
        66,68,3,26,13,0,67,66,1,0,0,0,67,68,1,0,0,0,68,7,1,0,0,0,69,70,7,
        1,0,0,70,9,1,0,0,0,71,72,7,2,0,0,72,11,1,0,0,0,73,77,3,14,7,0,74,
        75,5,18,0,0,75,77,3,42,21,0,76,73,1,0,0,0,76,74,1,0,0,0,77,13,1,
        0,0,0,78,83,3,40,20,0,79,80,5,26,0,0,80,82,3,40,20,0,81,79,1,0,0,
        0,82,85,1,0,0,0,83,81,1,0,0,0,83,84,1,0,0,0,84,15,1,0,0,0,85,83,
        1,0,0,0,86,87,7,3,0,0,87,17,1,0,0,0,88,89,3,20,10,0,89,19,1,0,0,
        0,90,91,7,4,0,0,91,21,1,0,0,0,92,97,5,12,0,0,93,94,5,13,0,0,94,97,
        3,24,12,0,95,97,5,23,0,0,96,92,1,0,0,0,96,93,1,0,0,0,96,95,1,0,0,
        0,97,23,1,0,0,0,98,103,3,40,20,0,99,100,5,27,0,0,100,102,3,40,20,
        0,101,99,1,0,0,0,102,105,1,0,0,0,103,101,1,0,0,0,103,104,1,0,0,0,
        104,25,1,0,0,0,105,103,1,0,0,0,106,107,5,14,0,0,107,108,3,28,14,
        0,108,27,1,0,0,0,109,110,5,15,0,0,110,111,5,24,0,0,111,112,3,30,
        15,0,112,113,5,25,0,0,113,121,1,0,0,0,114,115,5,16,0,0,115,116,5,
        24,0,0,116,117,3,30,15,0,117,118,5,25,0,0,118,121,1,0,0,0,119,121,
        3,38,19,0,120,109,1,0,0,0,120,114,1,0,0,0,120,119,1,0,0,0,121,29,
        1,0,0,0,122,127,3,32,16,0,123,124,5,26,0,0,124,126,3,32,16,0,125,
        123,1,0,0,0,126,129,1,0,0,0,127,125,1,0,0,0,127,128,1,0,0,0,128,
        31,1,0,0,0,129,127,1,0,0,0,130,131,3,34,17,0,131,134,5,29,0,0,132,
        135,5,34,0,0,133,135,3,42,21,0,134,132,1,0,0,0,134,133,1,0,0,0,135,
        149,1,0,0,0,136,137,3,34,17,0,137,140,5,30,0,0,138,141,5,34,0,0,
        139,141,3,42,21,0,140,138,1,0,0,0,140,139,1,0,0,0,141,149,1,0,0,
        0,142,143,3,34,17,0,143,144,5,35,0,0,144,149,1,0,0,0,145,146,3,34,
        17,0,146,147,5,36,0,0,147,149,1,0,0,0,148,130,1,0,0,0,148,136,1,
        0,0,0,148,142,1,0,0,0,148,145,1,0,0,0,149,33,1,0,0,0,150,155,3,36,
        18,0,151,152,5,28,0,0,152,154,3,36,18,0,153,151,1,0,0,0,154,157,
        1,0,0,0,155,153,1,0,0,0,155,156,1,0,0,0,156,35,1,0,0,0,157,155,1,
        0,0,0,158,159,7,5,0,0,159,37,1,0,0,0,160,161,3,34,17,0,161,164,5,
        29,0,0,162,165,5,34,0,0,163,165,3,42,21,0,164,162,1,0,0,0,164,163,
        1,0,0,0,165,179,1,0,0,0,166,167,3,34,17,0,167,170,5,30,0,0,168,171,
        5,34,0,0,169,171,3,42,21,0,170,168,1,0,0,0,170,169,1,0,0,0,171,179,
        1,0,0,0,172,173,3,34,17,0,173,174,5,35,0,0,174,179,1,0,0,0,175,176,
        3,34,17,0,176,177,5,36,0,0,177,179,1,0,0,0,178,160,1,0,0,0,178,166,
        1,0,0,0,178,172,1,0,0,0,178,175,1,0,0,0,179,39,1,0,0,0,180,181,5,
        32,0,0,181,41,1,0,0,0,182,183,5,31,0,0,183,43,1,0,0,0,16,46,59,67,
        76,83,96,103,120,127,134,140,148,155,164,170,178
    ]

class OciPolicyParser ( Parser ):

    grammarFileName = "OciPolicy.g4"

    atn = ATNDeserializer().deserialize(serializedATN())

    decisionsToDFA = [ DFA(ds, i) for i, ds in enumerate(atn.decisionToState) ]

    sharedContextCache = PredictionContextCache()

    literalNames = [ "<INVALID>", "<INVALID>", "<INVALID>", "<INVALID>", 
                     "<INVALID>", "<INVALID>", "<INVALID>", "<INVALID>", 
                     "<INVALID>", "<INVALID>", "<INVALID>", "<INVALID>", 
                     "<INVALID>", "<INVALID>", "<INVALID>", "<INVALID>", 
                     "<INVALID>", "<INVALID>", "<INVALID>", "<INVALID>", 
                     "<INVALID>", "<INVALID>", "<INVALID>", "<INVALID>", 
                     "'{'", "'}'", "','", "':'", "'.'", "'='", "'!='" ]

    symbolicNames = [ "<INVALID>", "ALLOW", "DENY", "ENDORSE", "ADMIT", 
                      "DEFINE", "GROUP", "DYNAMIC_GROUP", "ANY_USER", "ANY_GROUP", 
                      "TO", "IN", "TENANCY", "COMPARTMENT", "WHERE", "ALL", 
                      "ANY", "AS", "ID", "INSPECT", "READ", "USE", "MANAGE", 
                      "ANY_TENANCY", "LBRACE", "RBRACE", "COMMA", "COLON", 
                      "DOT", "EQ", "NEQ", "OCID", "IDENTIFIER", "ALL_RESOURCES", 
                      "STRING", "REGEX_MATCH", "NEQ_REGEX_MATCH", "WS", 
                      "NEWLINE" ]

    RULE_policyStatement = 0
    RULE_defineStatement = 1
    RULE_definableType = 2
    RULE_accessStatement = 3
    RULE_effect = 4
    RULE_subject = 5
    RULE_principalSpec = 6
    RULE_principalList = 7
    RULE_verb = 8
    RULE_resource = 9
    RULE_resourceId = 10
    RULE_location = 11
    RULE_compartmentPath = 12
    RULE_whereClause = 13
    RULE_condition = 14
    RULE_conditionList = 15
    RULE_conditionExpr = 16
    RULE_conditionLhs = 17
    RULE_conditionIdentifier = 18
    RULE_singleCondition = 19
    RULE_identifier = 20
    RULE_ocid = 21

    ruleNames =  [ "policyStatement", "defineStatement", "definableType", 
                   "accessStatement", "effect", "subject", "principalSpec", 
                   "principalList", "verb", "resource", "resourceId", "location", 
                   "compartmentPath", "whereClause", "condition", "conditionList", 
                   "conditionExpr", "conditionLhs", "conditionIdentifier", 
                   "singleCondition", "identifier", "ocid" ]

    EOF = Token.EOF
    ALLOW=1
    DENY=2
    ENDORSE=3
    ADMIT=4
    DEFINE=5
    GROUP=6
    DYNAMIC_GROUP=7
    ANY_USER=8
    ANY_GROUP=9
    TO=10
    IN=11
    TENANCY=12
    COMPARTMENT=13
    WHERE=14
    ALL=15
    ANY=16
    AS=17
    ID=18
    INSPECT=19
    READ=20
    USE=21
    MANAGE=22
    ANY_TENANCY=23
    LBRACE=24
    RBRACE=25
    COMMA=26
    COLON=27
    DOT=28
    EQ=29
    NEQ=30
    OCID=31
    IDENTIFIER=32
    ALL_RESOURCES=33
    STRING=34
    REGEX_MATCH=35
    NEQ_REGEX_MATCH=36
    WS=37
    NEWLINE=38

    def __init__(self, input:TokenStream, output:TextIO = sys.stdout):
        super().__init__(input, output)
        self.checkVersion("4.13.2")
        self._interp = ParserATNSimulator(self, self.atn, self.decisionsToDFA, self.sharedContextCache)
        self._predicates = None




    class PolicyStatementContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def defineStatement(self):
            return self.getTypedRuleContext(OciPolicyParser.DefineStatementContext,0)


        def accessStatement(self):
            return self.getTypedRuleContext(OciPolicyParser.AccessStatementContext,0)


        def getRuleIndex(self):
            return OciPolicyParser.RULE_policyStatement

        def enterRule(self, listener:ParseTreeListener):
            if hasattr( listener, "enterPolicyStatement" ):
                listener.enterPolicyStatement(self)

        def exitRule(self, listener:ParseTreeListener):
            if hasattr( listener, "exitPolicyStatement" ):
                listener.exitPolicyStatement(self)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitPolicyStatement" ):
                return visitor.visitPolicyStatement(self)
            else:
                return visitor.visitChildren(self)




    def policyStatement(self):

        localctx = OciPolicyParser.PolicyStatementContext(self, self._ctx, self.state)
        self.enterRule(localctx, 0, self.RULE_policyStatement)
        try:
            self.state = 46
            self._errHandler.sync(self)
            token = self._input.LA(1)
            if token in [5]:
                self.enterOuterAlt(localctx, 1)
                self.state = 44
                self.defineStatement()
                pass
            elif token in [1, 2, 3, 4]:
                self.enterOuterAlt(localctx, 2)
                self.state = 45
                self.accessStatement()
                pass
            else:
                raise NoViableAltException(self)

        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class DefineStatementContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser
            self.alias = None # IdentifierContext
            self.value = None # OcidContext

        def DEFINE(self):
            return self.getToken(OciPolicyParser.DEFINE, 0)

        def definableType(self):
            return self.getTypedRuleContext(OciPolicyParser.DefinableTypeContext,0)


        def AS(self):
            return self.getToken(OciPolicyParser.AS, 0)

        def identifier(self):
            return self.getTypedRuleContext(OciPolicyParser.IdentifierContext,0)


        def ocid(self):
            return self.getTypedRuleContext(OciPolicyParser.OcidContext,0)


        def getRuleIndex(self):
            return OciPolicyParser.RULE_defineStatement

        def enterRule(self, listener:ParseTreeListener):
            if hasattr( listener, "enterDefineStatement" ):
                listener.enterDefineStatement(self)

        def exitRule(self, listener:ParseTreeListener):
            if hasattr( listener, "exitDefineStatement" ):
                listener.exitDefineStatement(self)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitDefineStatement" ):
                return visitor.visitDefineStatement(self)
            else:
                return visitor.visitChildren(self)




    def defineStatement(self):

        localctx = OciPolicyParser.DefineStatementContext(self, self._ctx, self.state)
        self.enterRule(localctx, 2, self.RULE_defineStatement)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 48
            self.match(OciPolicyParser.DEFINE)
            self.state = 49
            self.definableType()
            self.state = 50
            localctx.alias = self.identifier()
            self.state = 51
            self.match(OciPolicyParser.AS)
            self.state = 52
            localctx.value = self.ocid()
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class DefinableTypeContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def TENANCY(self):
            return self.getToken(OciPolicyParser.TENANCY, 0)

        def GROUP(self):
            return self.getToken(OciPolicyParser.GROUP, 0)

        def DYNAMIC_GROUP(self):
            return self.getToken(OciPolicyParser.DYNAMIC_GROUP, 0)

        def getRuleIndex(self):
            return OciPolicyParser.RULE_definableType

        def enterRule(self, listener:ParseTreeListener):
            if hasattr( listener, "enterDefinableType" ):
                listener.enterDefinableType(self)

        def exitRule(self, listener:ParseTreeListener):
            if hasattr( listener, "exitDefinableType" ):
                listener.exitDefinableType(self)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitDefinableType" ):
                return visitor.visitDefinableType(self)
            else:
                return visitor.visitChildren(self)




    def definableType(self):

        localctx = OciPolicyParser.DefinableTypeContext(self, self._ctx, self.state)
        self.enterRule(localctx, 4, self.RULE_definableType)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 54
            _la = self._input.LA(1)
            if not((((_la) & ~0x3f) == 0 and ((1 << _la) & 4288) != 0)):
                self._errHandler.recoverInline(self)
            else:
                self._errHandler.reportMatch(self)
                self.consume()
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class AccessStatementContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def effect(self):
            return self.getTypedRuleContext(OciPolicyParser.EffectContext,0)


        def subject(self):
            return self.getTypedRuleContext(OciPolicyParser.SubjectContext,0)


        def TO(self):
            return self.getToken(OciPolicyParser.TO, 0)

        def verb(self):
            return self.getTypedRuleContext(OciPolicyParser.VerbContext,0)


        def resource(self):
            return self.getTypedRuleContext(OciPolicyParser.ResourceContext,0)


        def IN(self):
            return self.getToken(OciPolicyParser.IN, 0)

        def location(self):
            return self.getTypedRuleContext(OciPolicyParser.LocationContext,0)


        def principalSpec(self):
            return self.getTypedRuleContext(OciPolicyParser.PrincipalSpecContext,0)


        def whereClause(self):
            return self.getTypedRuleContext(OciPolicyParser.WhereClauseContext,0)


        def getRuleIndex(self):
            return OciPolicyParser.RULE_accessStatement

        def enterRule(self, listener:ParseTreeListener):
            if hasattr( listener, "enterAccessStatement" ):
                listener.enterAccessStatement(self)

        def exitRule(self, listener:ParseTreeListener):
            if hasattr( listener, "exitAccessStatement" ):
                listener.exitAccessStatement(self)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitAccessStatement" ):
                return visitor.visitAccessStatement(self)
            else:
                return visitor.visitChildren(self)




    def accessStatement(self):

        localctx = OciPolicyParser.AccessStatementContext(self, self._ctx, self.state)
        self.enterRule(localctx, 6, self.RULE_accessStatement)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 56
            self.effect()
            self.state = 57
            self.subject()
            self.state = 59
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            if _la==18 or _la==32:
                self.state = 58
                self.principalSpec()


            self.state = 61
            self.match(OciPolicyParser.TO)
            self.state = 62
            self.verb()
            self.state = 63
            self.resource()
            self.state = 64
            self.match(OciPolicyParser.IN)
            self.state = 65
            self.location()
            self.state = 67
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            if _la==14:
                self.state = 66
                self.whereClause()


        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class EffectContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def ALLOW(self):
            return self.getToken(OciPolicyParser.ALLOW, 0)

        def DENY(self):
            return self.getToken(OciPolicyParser.DENY, 0)

        def ENDORSE(self):
            return self.getToken(OciPolicyParser.ENDORSE, 0)

        def ADMIT(self):
            return self.getToken(OciPolicyParser.ADMIT, 0)

        def getRuleIndex(self):
            return OciPolicyParser.RULE_effect

        def enterRule(self, listener:ParseTreeListener):
            if hasattr( listener, "enterEffect" ):
                listener.enterEffect(self)

        def exitRule(self, listener:ParseTreeListener):
            if hasattr( listener, "exitEffect" ):
                listener.exitEffect(self)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitEffect" ):
                return visitor.visitEffect(self)
            else:
                return visitor.visitChildren(self)




    def effect(self):

        localctx = OciPolicyParser.EffectContext(self, self._ctx, self.state)
        self.enterRule(localctx, 8, self.RULE_effect)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 69
            _la = self._input.LA(1)
            if not((((_la) & ~0x3f) == 0 and ((1 << _la) & 30) != 0)):
                self._errHandler.recoverInline(self)
            else:
                self._errHandler.reportMatch(self)
                self.consume()
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class SubjectContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def GROUP(self):
            return self.getToken(OciPolicyParser.GROUP, 0)

        def DYNAMIC_GROUP(self):
            return self.getToken(OciPolicyParser.DYNAMIC_GROUP, 0)

        def ANY_USER(self):
            return self.getToken(OciPolicyParser.ANY_USER, 0)

        def ANY_GROUP(self):
            return self.getToken(OciPolicyParser.ANY_GROUP, 0)

        def getRuleIndex(self):
            return OciPolicyParser.RULE_subject

        def enterRule(self, listener:ParseTreeListener):
            if hasattr( listener, "enterSubject" ):
                listener.enterSubject(self)

        def exitRule(self, listener:ParseTreeListener):
            if hasattr( listener, "exitSubject" ):
                listener.exitSubject(self)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitSubject" ):
                return visitor.visitSubject(self)
            else:
                return visitor.visitChildren(self)




    def subject(self):

        localctx = OciPolicyParser.SubjectContext(self, self._ctx, self.state)
        self.enterRule(localctx, 10, self.RULE_subject)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 71
            _la = self._input.LA(1)
            if not((((_la) & ~0x3f) == 0 and ((1 << _la) & 960) != 0)):
                self._errHandler.recoverInline(self)
            else:
                self._errHandler.reportMatch(self)
                self.consume()
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class PrincipalSpecContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser
            self.principalOcid = None # OcidContext

        def principalList(self):
            return self.getTypedRuleContext(OciPolicyParser.PrincipalListContext,0)


        def ID(self):
            return self.getToken(OciPolicyParser.ID, 0)

        def ocid(self):
            return self.getTypedRuleContext(OciPolicyParser.OcidContext,0)


        def getRuleIndex(self):
            return OciPolicyParser.RULE_principalSpec

        def enterRule(self, listener:ParseTreeListener):
            if hasattr( listener, "enterPrincipalSpec" ):
                listener.enterPrincipalSpec(self)

        def exitRule(self, listener:ParseTreeListener):
            if hasattr( listener, "exitPrincipalSpec" ):
                listener.exitPrincipalSpec(self)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitPrincipalSpec" ):
                return visitor.visitPrincipalSpec(self)
            else:
                return visitor.visitChildren(self)




    def principalSpec(self):

        localctx = OciPolicyParser.PrincipalSpecContext(self, self._ctx, self.state)
        self.enterRule(localctx, 12, self.RULE_principalSpec)
        try:
            self.state = 76
            self._errHandler.sync(self)
            token = self._input.LA(1)
            if token in [32]:
                self.enterOuterAlt(localctx, 1)
                self.state = 73
                self.principalList()
                pass
            elif token in [18]:
                self.enterOuterAlt(localctx, 2)
                self.state = 74
                self.match(OciPolicyParser.ID)
                self.state = 75
                localctx.principalOcid = self.ocid()
                pass
            else:
                raise NoViableAltException(self)

        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class PrincipalListContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def identifier(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(OciPolicyParser.IdentifierContext)
            else:
                return self.getTypedRuleContext(OciPolicyParser.IdentifierContext,i)


        def COMMA(self, i:int=None):
            if i is None:
                return self.getTokens(OciPolicyParser.COMMA)
            else:
                return self.getToken(OciPolicyParser.COMMA, i)

        def getRuleIndex(self):
            return OciPolicyParser.RULE_principalList

        def enterRule(self, listener:ParseTreeListener):
            if hasattr( listener, "enterPrincipalList" ):
                listener.enterPrincipalList(self)

        def exitRule(self, listener:ParseTreeListener):
            if hasattr( listener, "exitPrincipalList" ):
                listener.exitPrincipalList(self)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitPrincipalList" ):
                return visitor.visitPrincipalList(self)
            else:
                return visitor.visitChildren(self)




    def principalList(self):

        localctx = OciPolicyParser.PrincipalListContext(self, self._ctx, self.state)
        self.enterRule(localctx, 14, self.RULE_principalList)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 78
            self.identifier()
            self.state = 83
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while _la==26:
                self.state = 79
                self.match(OciPolicyParser.COMMA)
                self.state = 80
                self.identifier()
                self.state = 85
                self._errHandler.sync(self)
                _la = self._input.LA(1)

        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class VerbContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def INSPECT(self):
            return self.getToken(OciPolicyParser.INSPECT, 0)

        def READ(self):
            return self.getToken(OciPolicyParser.READ, 0)

        def USE(self):
            return self.getToken(OciPolicyParser.USE, 0)

        def MANAGE(self):
            return self.getToken(OciPolicyParser.MANAGE, 0)

        def getRuleIndex(self):
            return OciPolicyParser.RULE_verb

        def enterRule(self, listener:ParseTreeListener):
            if hasattr( listener, "enterVerb" ):
                listener.enterVerb(self)

        def exitRule(self, listener:ParseTreeListener):
            if hasattr( listener, "exitVerb" ):
                listener.exitVerb(self)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitVerb" ):
                return visitor.visitVerb(self)
            else:
                return visitor.visitChildren(self)




    def verb(self):

        localctx = OciPolicyParser.VerbContext(self, self._ctx, self.state)
        self.enterRule(localctx, 16, self.RULE_verb)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 86
            _la = self._input.LA(1)
            if not((((_la) & ~0x3f) == 0 and ((1 << _la) & 7864320) != 0)):
                self._errHandler.recoverInline(self)
            else:
                self._errHandler.reportMatch(self)
                self.consume()
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class ResourceContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def resourceId(self):
            return self.getTypedRuleContext(OciPolicyParser.ResourceIdContext,0)


        def getRuleIndex(self):
            return OciPolicyParser.RULE_resource

        def enterRule(self, listener:ParseTreeListener):
            if hasattr( listener, "enterResource" ):
                listener.enterResource(self)

        def exitRule(self, listener:ParseTreeListener):
            if hasattr( listener, "exitResource" ):
                listener.exitResource(self)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitResource" ):
                return visitor.visitResource(self)
            else:
                return visitor.visitChildren(self)




    def resource(self):

        localctx = OciPolicyParser.ResourceContext(self, self._ctx, self.state)
        self.enterRule(localctx, 18, self.RULE_resource)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 88
            self.resourceId()
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class ResourceIdContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def ALL_RESOURCES(self):
            return self.getToken(OciPolicyParser.ALL_RESOURCES, 0)

        def IDENTIFIER(self):
            return self.getToken(OciPolicyParser.IDENTIFIER, 0)

        def getRuleIndex(self):
            return OciPolicyParser.RULE_resourceId

        def enterRule(self, listener:ParseTreeListener):
            if hasattr( listener, "enterResourceId" ):
                listener.enterResourceId(self)

        def exitRule(self, listener:ParseTreeListener):
            if hasattr( listener, "exitResourceId" ):
                listener.exitResourceId(self)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitResourceId" ):
                return visitor.visitResourceId(self)
            else:
                return visitor.visitChildren(self)




    def resourceId(self):

        localctx = OciPolicyParser.ResourceIdContext(self, self._ctx, self.state)
        self.enterRule(localctx, 20, self.RULE_resourceId)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 90
            _la = self._input.LA(1)
            if not(_la==32 or _la==33):
                self._errHandler.recoverInline(self)
            else:
                self._errHandler.reportMatch(self)
                self.consume()
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class LocationContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def TENANCY(self):
            return self.getToken(OciPolicyParser.TENANCY, 0)

        def COMPARTMENT(self):
            return self.getToken(OciPolicyParser.COMPARTMENT, 0)

        def compartmentPath(self):
            return self.getTypedRuleContext(OciPolicyParser.CompartmentPathContext,0)


        def ANY_TENANCY(self):
            return self.getToken(OciPolicyParser.ANY_TENANCY, 0)

        def getRuleIndex(self):
            return OciPolicyParser.RULE_location

        def enterRule(self, listener:ParseTreeListener):
            if hasattr( listener, "enterLocation" ):
                listener.enterLocation(self)

        def exitRule(self, listener:ParseTreeListener):
            if hasattr( listener, "exitLocation" ):
                listener.exitLocation(self)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitLocation" ):
                return visitor.visitLocation(self)
            else:
                return visitor.visitChildren(self)




    def location(self):

        localctx = OciPolicyParser.LocationContext(self, self._ctx, self.state)
        self.enterRule(localctx, 22, self.RULE_location)
        try:
            self.state = 96
            self._errHandler.sync(self)
            token = self._input.LA(1)
            if token in [12]:
                self.enterOuterAlt(localctx, 1)
                self.state = 92
                self.match(OciPolicyParser.TENANCY)
                pass
            elif token in [13]:
                self.enterOuterAlt(localctx, 2)
                self.state = 93
                self.match(OciPolicyParser.COMPARTMENT)
                self.state = 94
                self.compartmentPath()
                pass
            elif token in [23]:
                self.enterOuterAlt(localctx, 3)
                self.state = 95
                self.match(OciPolicyParser.ANY_TENANCY)
                pass
            else:
                raise NoViableAltException(self)

        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class CompartmentPathContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def identifier(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(OciPolicyParser.IdentifierContext)
            else:
                return self.getTypedRuleContext(OciPolicyParser.IdentifierContext,i)


        def COLON(self, i:int=None):
            if i is None:
                return self.getTokens(OciPolicyParser.COLON)
            else:
                return self.getToken(OciPolicyParser.COLON, i)

        def getRuleIndex(self):
            return OciPolicyParser.RULE_compartmentPath

        def enterRule(self, listener:ParseTreeListener):
            if hasattr( listener, "enterCompartmentPath" ):
                listener.enterCompartmentPath(self)

        def exitRule(self, listener:ParseTreeListener):
            if hasattr( listener, "exitCompartmentPath" ):
                listener.exitCompartmentPath(self)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitCompartmentPath" ):
                return visitor.visitCompartmentPath(self)
            else:
                return visitor.visitChildren(self)




    def compartmentPath(self):

        localctx = OciPolicyParser.CompartmentPathContext(self, self._ctx, self.state)
        self.enterRule(localctx, 24, self.RULE_compartmentPath)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 98
            self.identifier()
            self.state = 103
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while _la==27:
                self.state = 99
                self.match(OciPolicyParser.COLON)
                self.state = 100
                self.identifier()
                self.state = 105
                self._errHandler.sync(self)
                _la = self._input.LA(1)

        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class WhereClauseContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def WHERE(self):
            return self.getToken(OciPolicyParser.WHERE, 0)

        def condition(self):
            return self.getTypedRuleContext(OciPolicyParser.ConditionContext,0)


        def getRuleIndex(self):
            return OciPolicyParser.RULE_whereClause

        def enterRule(self, listener:ParseTreeListener):
            if hasattr( listener, "enterWhereClause" ):
                listener.enterWhereClause(self)

        def exitRule(self, listener:ParseTreeListener):
            if hasattr( listener, "exitWhereClause" ):
                listener.exitWhereClause(self)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitWhereClause" ):
                return visitor.visitWhereClause(self)
            else:
                return visitor.visitChildren(self)




    def whereClause(self):

        localctx = OciPolicyParser.WhereClauseContext(self, self._ctx, self.state)
        self.enterRule(localctx, 26, self.RULE_whereClause)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 106
            self.match(OciPolicyParser.WHERE)
            self.state = 107
            self.condition()
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class ConditionContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def ALL(self):
            return self.getToken(OciPolicyParser.ALL, 0)

        def LBRACE(self):
            return self.getToken(OciPolicyParser.LBRACE, 0)

        def conditionList(self):
            return self.getTypedRuleContext(OciPolicyParser.ConditionListContext,0)


        def RBRACE(self):
            return self.getToken(OciPolicyParser.RBRACE, 0)

        def ANY(self):
            return self.getToken(OciPolicyParser.ANY, 0)

        def singleCondition(self):
            return self.getTypedRuleContext(OciPolicyParser.SingleConditionContext,0)


        def getRuleIndex(self):
            return OciPolicyParser.RULE_condition

        def enterRule(self, listener:ParseTreeListener):
            if hasattr( listener, "enterCondition" ):
                listener.enterCondition(self)

        def exitRule(self, listener:ParseTreeListener):
            if hasattr( listener, "exitCondition" ):
                listener.exitCondition(self)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitCondition" ):
                return visitor.visitCondition(self)
            else:
                return visitor.visitChildren(self)




    def condition(self):

        localctx = OciPolicyParser.ConditionContext(self, self._ctx, self.state)
        self.enterRule(localctx, 28, self.RULE_condition)
        try:
            self.state = 120
            self._errHandler.sync(self)
            token = self._input.LA(1)
            if token in [15]:
                self.enterOuterAlt(localctx, 1)
                self.state = 109
                self.match(OciPolicyParser.ALL)
                self.state = 110
                self.match(OciPolicyParser.LBRACE)
                self.state = 111
                self.conditionList()
                self.state = 112
                self.match(OciPolicyParser.RBRACE)
                pass
            elif token in [16]:
                self.enterOuterAlt(localctx, 2)
                self.state = 114
                self.match(OciPolicyParser.ANY)
                self.state = 115
                self.match(OciPolicyParser.LBRACE)
                self.state = 116
                self.conditionList()
                self.state = 117
                self.match(OciPolicyParser.RBRACE)
                pass
            elif token in [6, 18, 32]:
                self.enterOuterAlt(localctx, 3)
                self.state = 119
                self.singleCondition()
                pass
            else:
                raise NoViableAltException(self)

        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class ConditionListContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def conditionExpr(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(OciPolicyParser.ConditionExprContext)
            else:
                return self.getTypedRuleContext(OciPolicyParser.ConditionExprContext,i)


        def COMMA(self, i:int=None):
            if i is None:
                return self.getTokens(OciPolicyParser.COMMA)
            else:
                return self.getToken(OciPolicyParser.COMMA, i)

        def getRuleIndex(self):
            return OciPolicyParser.RULE_conditionList

        def enterRule(self, listener:ParseTreeListener):
            if hasattr( listener, "enterConditionList" ):
                listener.enterConditionList(self)

        def exitRule(self, listener:ParseTreeListener):
            if hasattr( listener, "exitConditionList" ):
                listener.exitConditionList(self)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitConditionList" ):
                return visitor.visitConditionList(self)
            else:
                return visitor.visitChildren(self)




    def conditionList(self):

        localctx = OciPolicyParser.ConditionListContext(self, self._ctx, self.state)
        self.enterRule(localctx, 30, self.RULE_conditionList)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 122
            self.conditionExpr()
            self.state = 127
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while _la==26:
                self.state = 123
                self.match(OciPolicyParser.COMMA)
                self.state = 124
                self.conditionExpr()
                self.state = 129
                self._errHandler.sync(self)
                _la = self._input.LA(1)

        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class ConditionExprContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def conditionLhs(self):
            return self.getTypedRuleContext(OciPolicyParser.ConditionLhsContext,0)


        def EQ(self):
            return self.getToken(OciPolicyParser.EQ, 0)

        def STRING(self):
            return self.getToken(OciPolicyParser.STRING, 0)

        def ocid(self):
            return self.getTypedRuleContext(OciPolicyParser.OcidContext,0)


        def NEQ(self):
            return self.getToken(OciPolicyParser.NEQ, 0)

        def REGEX_MATCH(self):
            return self.getToken(OciPolicyParser.REGEX_MATCH, 0)

        def NEQ_REGEX_MATCH(self):
            return self.getToken(OciPolicyParser.NEQ_REGEX_MATCH, 0)

        def getRuleIndex(self):
            return OciPolicyParser.RULE_conditionExpr

        def enterRule(self, listener:ParseTreeListener):
            if hasattr( listener, "enterConditionExpr" ):
                listener.enterConditionExpr(self)

        def exitRule(self, listener:ParseTreeListener):
            if hasattr( listener, "exitConditionExpr" ):
                listener.exitConditionExpr(self)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitConditionExpr" ):
                return visitor.visitConditionExpr(self)
            else:
                return visitor.visitChildren(self)




    def conditionExpr(self):

        localctx = OciPolicyParser.ConditionExprContext(self, self._ctx, self.state)
        self.enterRule(localctx, 32, self.RULE_conditionExpr)
        try:
            self.state = 148
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input,11,self._ctx)
            if la_ == 1:
                self.enterOuterAlt(localctx, 1)
                self.state = 130
                self.conditionLhs()
                self.state = 131
                self.match(OciPolicyParser.EQ)
                self.state = 134
                self._errHandler.sync(self)
                token = self._input.LA(1)
                if token in [34]:
                    self.state = 132
                    self.match(OciPolicyParser.STRING)
                    pass
                elif token in [31]:
                    self.state = 133
                    self.ocid()
                    pass
                else:
                    raise NoViableAltException(self)

                pass

            elif la_ == 2:
                self.enterOuterAlt(localctx, 2)
                self.state = 136
                self.conditionLhs()
                self.state = 137
                self.match(OciPolicyParser.NEQ)
                self.state = 140
                self._errHandler.sync(self)
                token = self._input.LA(1)
                if token in [34]:
                    self.state = 138
                    self.match(OciPolicyParser.STRING)
                    pass
                elif token in [31]:
                    self.state = 139
                    self.ocid()
                    pass
                else:
                    raise NoViableAltException(self)

                pass

            elif la_ == 3:
                self.enterOuterAlt(localctx, 3)
                self.state = 142
                self.conditionLhs()
                self.state = 143
                self.match(OciPolicyParser.REGEX_MATCH)
                pass

            elif la_ == 4:
                self.enterOuterAlt(localctx, 4)
                self.state = 145
                self.conditionLhs()
                self.state = 146
                self.match(OciPolicyParser.NEQ_REGEX_MATCH)
                pass


        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class ConditionLhsContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def conditionIdentifier(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(OciPolicyParser.ConditionIdentifierContext)
            else:
                return self.getTypedRuleContext(OciPolicyParser.ConditionIdentifierContext,i)


        def DOT(self, i:int=None):
            if i is None:
                return self.getTokens(OciPolicyParser.DOT)
            else:
                return self.getToken(OciPolicyParser.DOT, i)

        def getRuleIndex(self):
            return OciPolicyParser.RULE_conditionLhs

        def enterRule(self, listener:ParseTreeListener):
            if hasattr( listener, "enterConditionLhs" ):
                listener.enterConditionLhs(self)

        def exitRule(self, listener:ParseTreeListener):
            if hasattr( listener, "exitConditionLhs" ):
                listener.exitConditionLhs(self)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitConditionLhs" ):
                return visitor.visitConditionLhs(self)
            else:
                return visitor.visitChildren(self)




    def conditionLhs(self):

        localctx = OciPolicyParser.ConditionLhsContext(self, self._ctx, self.state)
        self.enterRule(localctx, 34, self.RULE_conditionLhs)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 150
            self.conditionIdentifier()
            self.state = 155
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while _la==28:
                self.state = 151
                self.match(OciPolicyParser.DOT)
                self.state = 152
                self.conditionIdentifier()
                self.state = 157
                self._errHandler.sync(self)
                _la = self._input.LA(1)

        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class ConditionIdentifierContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def IDENTIFIER(self):
            return self.getToken(OciPolicyParser.IDENTIFIER, 0)

        def GROUP(self):
            return self.getToken(OciPolicyParser.GROUP, 0)

        def ID(self):
            return self.getToken(OciPolicyParser.ID, 0)

        def getRuleIndex(self):
            return OciPolicyParser.RULE_conditionIdentifier

        def enterRule(self, listener:ParseTreeListener):
            if hasattr( listener, "enterConditionIdentifier" ):
                listener.enterConditionIdentifier(self)

        def exitRule(self, listener:ParseTreeListener):
            if hasattr( listener, "exitConditionIdentifier" ):
                listener.exitConditionIdentifier(self)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitConditionIdentifier" ):
                return visitor.visitConditionIdentifier(self)
            else:
                return visitor.visitChildren(self)




    def conditionIdentifier(self):

        localctx = OciPolicyParser.ConditionIdentifierContext(self, self._ctx, self.state)
        self.enterRule(localctx, 36, self.RULE_conditionIdentifier)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 158
            _la = self._input.LA(1)
            if not((((_la) & ~0x3f) == 0 and ((1 << _la) & 4295229504) != 0)):
                self._errHandler.recoverInline(self)
            else:
                self._errHandler.reportMatch(self)
                self.consume()
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class SingleConditionContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def conditionLhs(self):
            return self.getTypedRuleContext(OciPolicyParser.ConditionLhsContext,0)


        def EQ(self):
            return self.getToken(OciPolicyParser.EQ, 0)

        def STRING(self):
            return self.getToken(OciPolicyParser.STRING, 0)

        def ocid(self):
            return self.getTypedRuleContext(OciPolicyParser.OcidContext,0)


        def NEQ(self):
            return self.getToken(OciPolicyParser.NEQ, 0)

        def REGEX_MATCH(self):
            return self.getToken(OciPolicyParser.REGEX_MATCH, 0)

        def NEQ_REGEX_MATCH(self):
            return self.getToken(OciPolicyParser.NEQ_REGEX_MATCH, 0)

        def getRuleIndex(self):
            return OciPolicyParser.RULE_singleCondition

        def enterRule(self, listener:ParseTreeListener):
            if hasattr( listener, "enterSingleCondition" ):
                listener.enterSingleCondition(self)

        def exitRule(self, listener:ParseTreeListener):
            if hasattr( listener, "exitSingleCondition" ):
                listener.exitSingleCondition(self)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitSingleCondition" ):
                return visitor.visitSingleCondition(self)
            else:
                return visitor.visitChildren(self)




    def singleCondition(self):

        localctx = OciPolicyParser.SingleConditionContext(self, self._ctx, self.state)
        self.enterRule(localctx, 38, self.RULE_singleCondition)
        try:
            self.state = 178
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input,15,self._ctx)
            if la_ == 1:
                self.enterOuterAlt(localctx, 1)
                self.state = 160
                self.conditionLhs()
                self.state = 161
                self.match(OciPolicyParser.EQ)
                self.state = 164
                self._errHandler.sync(self)
                token = self._input.LA(1)
                if token in [34]:
                    self.state = 162
                    self.match(OciPolicyParser.STRING)
                    pass
                elif token in [31]:
                    self.state = 163
                    self.ocid()
                    pass
                else:
                    raise NoViableAltException(self)

                pass

            elif la_ == 2:
                self.enterOuterAlt(localctx, 2)
                self.state = 166
                self.conditionLhs()
                self.state = 167
                self.match(OciPolicyParser.NEQ)
                self.state = 170
                self._errHandler.sync(self)
                token = self._input.LA(1)
                if token in [34]:
                    self.state = 168
                    self.match(OciPolicyParser.STRING)
                    pass
                elif token in [31]:
                    self.state = 169
                    self.ocid()
                    pass
                else:
                    raise NoViableAltException(self)

                pass

            elif la_ == 3:
                self.enterOuterAlt(localctx, 3)
                self.state = 172
                self.conditionLhs()
                self.state = 173
                self.match(OciPolicyParser.REGEX_MATCH)
                pass

            elif la_ == 4:
                self.enterOuterAlt(localctx, 4)
                self.state = 175
                self.conditionLhs()
                self.state = 176
                self.match(OciPolicyParser.NEQ_REGEX_MATCH)
                pass


        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class IdentifierContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def IDENTIFIER(self):
            return self.getToken(OciPolicyParser.IDENTIFIER, 0)

        def getRuleIndex(self):
            return OciPolicyParser.RULE_identifier

        def enterRule(self, listener:ParseTreeListener):
            if hasattr( listener, "enterIdentifier" ):
                listener.enterIdentifier(self)

        def exitRule(self, listener:ParseTreeListener):
            if hasattr( listener, "exitIdentifier" ):
                listener.exitIdentifier(self)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitIdentifier" ):
                return visitor.visitIdentifier(self)
            else:
                return visitor.visitChildren(self)




    def identifier(self):

        localctx = OciPolicyParser.IdentifierContext(self, self._ctx, self.state)
        self.enterRule(localctx, 40, self.RULE_identifier)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 180
            self.match(OciPolicyParser.IDENTIFIER)
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class OcidContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def OCID(self):
            return self.getToken(OciPolicyParser.OCID, 0)

        def getRuleIndex(self):
            return OciPolicyParser.RULE_ocid

        def enterRule(self, listener:ParseTreeListener):
            if hasattr( listener, "enterOcid" ):
                listener.enterOcid(self)

        def exitRule(self, listener:ParseTreeListener):
            if hasattr( listener, "exitOcid" ):
                listener.exitOcid(self)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitOcid" ):
                return visitor.visitOcid(self)
            else:
                return visitor.visitChildren(self)




    def ocid(self):

        localctx = OciPolicyParser.OcidContext(self, self._ctx, self.state)
        self.enterRule(localctx, 42, self.RULE_ocid)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 182
            self.match(OciPolicyParser.OCID)
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx





