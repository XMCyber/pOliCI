# Generated from grammar/OciPolicy.g4 by ANTLR 4.13.2
from antlr4 import *
if "." in __name__:
    from .OciPolicyParser import OciPolicyParser
else:
    from OciPolicyParser import OciPolicyParser

# This class defines a complete listener for a parse tree produced by OciPolicyParser.
class OciPolicyListener(ParseTreeListener):

    # Enter a parse tree produced by OciPolicyParser#policyStatement.
    def enterPolicyStatement(self, ctx:OciPolicyParser.PolicyStatementContext):
        pass

    # Exit a parse tree produced by OciPolicyParser#policyStatement.
    def exitPolicyStatement(self, ctx:OciPolicyParser.PolicyStatementContext):
        pass


    # Enter a parse tree produced by OciPolicyParser#defineStatement.
    def enterDefineStatement(self, ctx:OciPolicyParser.DefineStatementContext):
        pass

    # Exit a parse tree produced by OciPolicyParser#defineStatement.
    def exitDefineStatement(self, ctx:OciPolicyParser.DefineStatementContext):
        pass


    # Enter a parse tree produced by OciPolicyParser#definableType.
    def enterDefinableType(self, ctx:OciPolicyParser.DefinableTypeContext):
        pass

    # Exit a parse tree produced by OciPolicyParser#definableType.
    def exitDefinableType(self, ctx:OciPolicyParser.DefinableTypeContext):
        pass


    # Enter a parse tree produced by OciPolicyParser#accessStatement.
    def enterAccessStatement(self, ctx:OciPolicyParser.AccessStatementContext):
        pass

    # Exit a parse tree produced by OciPolicyParser#accessStatement.
    def exitAccessStatement(self, ctx:OciPolicyParser.AccessStatementContext):
        pass


    # Enter a parse tree produced by OciPolicyParser#effect.
    def enterEffect(self, ctx:OciPolicyParser.EffectContext):
        pass

    # Exit a parse tree produced by OciPolicyParser#effect.
    def exitEffect(self, ctx:OciPolicyParser.EffectContext):
        pass


    # Enter a parse tree produced by OciPolicyParser#subject.
    def enterSubject(self, ctx:OciPolicyParser.SubjectContext):
        pass

    # Exit a parse tree produced by OciPolicyParser#subject.
    def exitSubject(self, ctx:OciPolicyParser.SubjectContext):
        pass


    # Enter a parse tree produced by OciPolicyParser#principalSpec.
    def enterPrincipalSpec(self, ctx:OciPolicyParser.PrincipalSpecContext):
        pass

    # Exit a parse tree produced by OciPolicyParser#principalSpec.
    def exitPrincipalSpec(self, ctx:OciPolicyParser.PrincipalSpecContext):
        pass


    # Enter a parse tree produced by OciPolicyParser#principalList.
    def enterPrincipalList(self, ctx:OciPolicyParser.PrincipalListContext):
        pass

    # Exit a parse tree produced by OciPolicyParser#principalList.
    def exitPrincipalList(self, ctx:OciPolicyParser.PrincipalListContext):
        pass


    # Enter a parse tree produced by OciPolicyParser#verb.
    def enterVerb(self, ctx:OciPolicyParser.VerbContext):
        pass

    # Exit a parse tree produced by OciPolicyParser#verb.
    def exitVerb(self, ctx:OciPolicyParser.VerbContext):
        pass


    # Enter a parse tree produced by OciPolicyParser#resource.
    def enterResource(self, ctx:OciPolicyParser.ResourceContext):
        pass

    # Exit a parse tree produced by OciPolicyParser#resource.
    def exitResource(self, ctx:OciPolicyParser.ResourceContext):
        pass


    # Enter a parse tree produced by OciPolicyParser#resourceId.
    def enterResourceId(self, ctx:OciPolicyParser.ResourceIdContext):
        pass

    # Exit a parse tree produced by OciPolicyParser#resourceId.
    def exitResourceId(self, ctx:OciPolicyParser.ResourceIdContext):
        pass


    # Enter a parse tree produced by OciPolicyParser#location.
    def enterLocation(self, ctx:OciPolicyParser.LocationContext):
        pass

    # Exit a parse tree produced by OciPolicyParser#location.
    def exitLocation(self, ctx:OciPolicyParser.LocationContext):
        pass


    # Enter a parse tree produced by OciPolicyParser#compartmentPath.
    def enterCompartmentPath(self, ctx:OciPolicyParser.CompartmentPathContext):
        pass

    # Exit a parse tree produced by OciPolicyParser#compartmentPath.
    def exitCompartmentPath(self, ctx:OciPolicyParser.CompartmentPathContext):
        pass


    # Enter a parse tree produced by OciPolicyParser#whereClause.
    def enterWhereClause(self, ctx:OciPolicyParser.WhereClauseContext):
        pass

    # Exit a parse tree produced by OciPolicyParser#whereClause.
    def exitWhereClause(self, ctx:OciPolicyParser.WhereClauseContext):
        pass


    # Enter a parse tree produced by OciPolicyParser#condition.
    def enterCondition(self, ctx:OciPolicyParser.ConditionContext):
        pass

    # Exit a parse tree produced by OciPolicyParser#condition.
    def exitCondition(self, ctx:OciPolicyParser.ConditionContext):
        pass


    # Enter a parse tree produced by OciPolicyParser#conditionList.
    def enterConditionList(self, ctx:OciPolicyParser.ConditionListContext):
        pass

    # Exit a parse tree produced by OciPolicyParser#conditionList.
    def exitConditionList(self, ctx:OciPolicyParser.ConditionListContext):
        pass


    # Enter a parse tree produced by OciPolicyParser#conditionExpr.
    def enterConditionExpr(self, ctx:OciPolicyParser.ConditionExprContext):
        pass

    # Exit a parse tree produced by OciPolicyParser#conditionExpr.
    def exitConditionExpr(self, ctx:OciPolicyParser.ConditionExprContext):
        pass


    # Enter a parse tree produced by OciPolicyParser#conditionLhs.
    def enterConditionLhs(self, ctx:OciPolicyParser.ConditionLhsContext):
        pass

    # Exit a parse tree produced by OciPolicyParser#conditionLhs.
    def exitConditionLhs(self, ctx:OciPolicyParser.ConditionLhsContext):
        pass


    # Enter a parse tree produced by OciPolicyParser#conditionIdentifier.
    def enterConditionIdentifier(self, ctx:OciPolicyParser.ConditionIdentifierContext):
        pass

    # Exit a parse tree produced by OciPolicyParser#conditionIdentifier.
    def exitConditionIdentifier(self, ctx:OciPolicyParser.ConditionIdentifierContext):
        pass


    # Enter a parse tree produced by OciPolicyParser#singleCondition.
    def enterSingleCondition(self, ctx:OciPolicyParser.SingleConditionContext):
        pass

    # Exit a parse tree produced by OciPolicyParser#singleCondition.
    def exitSingleCondition(self, ctx:OciPolicyParser.SingleConditionContext):
        pass


    # Enter a parse tree produced by OciPolicyParser#identifier.
    def enterIdentifier(self, ctx:OciPolicyParser.IdentifierContext):
        pass

    # Exit a parse tree produced by OciPolicyParser#identifier.
    def exitIdentifier(self, ctx:OciPolicyParser.IdentifierContext):
        pass


    # Enter a parse tree produced by OciPolicyParser#ocid.
    def enterOcid(self, ctx:OciPolicyParser.OcidContext):
        pass

    # Exit a parse tree produced by OciPolicyParser#ocid.
    def exitOcid(self, ctx:OciPolicyParser.OcidContext):
        pass



del OciPolicyParser