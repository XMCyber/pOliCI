# Generated from grammar/OciPolicy.g4 by ANTLR 4.13.2
from antlr4 import *
if "." in __name__:
    from .OciPolicyParser import OciPolicyParser
else:
    from OciPolicyParser import OciPolicyParser

# This class defines a complete generic visitor for a parse tree produced by OciPolicyParser.

class OciPolicyVisitor(ParseTreeVisitor):

    # Visit a parse tree produced by OciPolicyParser#policyStatement.
    def visitPolicyStatement(self, ctx:OciPolicyParser.PolicyStatementContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by OciPolicyParser#defineStatement.
    def visitDefineStatement(self, ctx:OciPolicyParser.DefineStatementContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by OciPolicyParser#definableType.
    def visitDefinableType(self, ctx:OciPolicyParser.DefinableTypeContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by OciPolicyParser#accessStatement.
    def visitAccessStatement(self, ctx:OciPolicyParser.AccessStatementContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by OciPolicyParser#effect.
    def visitEffect(self, ctx:OciPolicyParser.EffectContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by OciPolicyParser#subject.
    def visitSubject(self, ctx:OciPolicyParser.SubjectContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by OciPolicyParser#principalSpec.
    def visitPrincipalSpec(self, ctx:OciPolicyParser.PrincipalSpecContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by OciPolicyParser#principalList.
    def visitPrincipalList(self, ctx:OciPolicyParser.PrincipalListContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by OciPolicyParser#verb.
    def visitVerb(self, ctx:OciPolicyParser.VerbContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by OciPolicyParser#resource.
    def visitResource(self, ctx:OciPolicyParser.ResourceContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by OciPolicyParser#resourceId.
    def visitResourceId(self, ctx:OciPolicyParser.ResourceIdContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by OciPolicyParser#location.
    def visitLocation(self, ctx:OciPolicyParser.LocationContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by OciPolicyParser#compartmentPath.
    def visitCompartmentPath(self, ctx:OciPolicyParser.CompartmentPathContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by OciPolicyParser#whereClause.
    def visitWhereClause(self, ctx:OciPolicyParser.WhereClauseContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by OciPolicyParser#condition.
    def visitCondition(self, ctx:OciPolicyParser.ConditionContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by OciPolicyParser#conditionList.
    def visitConditionList(self, ctx:OciPolicyParser.ConditionListContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by OciPolicyParser#conditionExpr.
    def visitConditionExpr(self, ctx:OciPolicyParser.ConditionExprContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by OciPolicyParser#conditionLhs.
    def visitConditionLhs(self, ctx:OciPolicyParser.ConditionLhsContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by OciPolicyParser#conditionIdentifier.
    def visitConditionIdentifier(self, ctx:OciPolicyParser.ConditionIdentifierContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by OciPolicyParser#singleCondition.
    def visitSingleCondition(self, ctx:OciPolicyParser.SingleConditionContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by OciPolicyParser#identifier.
    def visitIdentifier(self, ctx:OciPolicyParser.IdentifierContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by OciPolicyParser#ocid.
    def visitOcid(self, ctx:OciPolicyParser.OcidContext):
        return self.visitChildren(ctx)



del OciPolicyParser