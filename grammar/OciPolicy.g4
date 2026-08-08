grammar OciPolicy;

// Parser rules
policyStatement
  : defineStatement
  | accessStatement
  ;

defineStatement
  : DEFINE definableType alias=identifier AS value=ocid
  ;

definableType
  : TENANCY
  | GROUP
  | DYNAMIC_GROUP
  ;

accessStatement
  : effect subject principalSpec? TO verb resource IN location whereClause?
  ;

effect
  : ALLOW
  | DENY
  | ENDORSE
  | ADMIT
  ;

subject
  : GROUP
  | DYNAMIC_GROUP
  | ANY_USER
  | ANY_GROUP
  ;

principalSpec
  : principalList
  | ID principalOcid=ocid
  ;

principalList
  : identifier (COMMA identifier)*
  ;

verb
  : INSPECT
  | READ
  | USE
  | MANAGE
  ;

resource
  : resourceId
  ;

resourceId
  : ALL_RESOURCES
  | IDENTIFIER
  ;

location
  : TENANCY
  | COMPARTMENT compartmentPath
  | ANY_TENANCY
  ;

compartmentPath
  : identifier (COLON identifier)*
  ;

whereClause
  : WHERE condition
  ;

condition
  : ALL LBRACE conditionList RBRACE
  | ANY LBRACE conditionList RBRACE
  | singleCondition
  ;

conditionList
  : conditionExpr (COMMA conditionExpr)*
  ;

conditionExpr
  : conditionLhs EQ (STRING | ocid)
  | conditionLhs NEQ (STRING | ocid)
  | conditionLhs REGEX_MATCH
  | conditionLhs NEQ_REGEX_MATCH
  ;

conditionLhs
  : conditionIdentifier (DOT conditionIdentifier)*
  ;

// In conditions, path segments can be reserved words (e.g. target.group.name, request.principal.id)
conditionIdentifier
  : IDENTIFIER
  | GROUP
  | ID
  ;

singleCondition
  : conditionLhs EQ (STRING | ocid)
  | conditionLhs NEQ (STRING | ocid)
  | conditionLhs REGEX_MATCH
  | conditionLhs NEQ_REGEX_MATCH
  ;

identifier
  : IDENTIFIER
  ;

ocid
  : OCID
  ;

// Lexer rules (case-insensitive via fragments)
fragment A : [aA]; fragment B : [bB]; fragment C : [cC]; fragment D : [dD];
fragment E : [eE]; fragment F : [fF]; fragment G : [gG]; fragment H : [hH];
fragment I : [iI]; fragment J : [jJ]; fragment K : [kK]; fragment L : [lL];
fragment M : [mM]; fragment N : [nN]; fragment O : [oO]; fragment P : [pP];
fragment Q : [qQ]; fragment R : [rR]; fragment S : [sS]; fragment T : [tT];
fragment U : [uU]; fragment V : [vV]; fragment W : [wW]; fragment X : [xX];
fragment Y : [yY]; fragment Z : [zZ];

ALLOW      : A L L O W ;
DENY       : D E N Y ;
ENDORSE    : E N D O R S E ;
ADMIT      : A D M I T ;
DEFINE     : D E F I N E ;
GROUP      : G R O U P ;
DYNAMIC_GROUP : D Y N A M I C '-' G R O U P ;
ANY_USER   : A N Y '-' U S E R ;
ANY_GROUP  : A N Y '-' G R O U P ;
TO         : T O ;
IN         : I N ;
TENANCY    : T E N A N C Y ;
COMPARTMENT : C O M P A R T M E N T ;
WHERE      : W H E R E ;
ALL        : A L L ;
ANY        : A N Y ;
AS         : A S ;
ID         : I D ;
INSPECT    : I N S P E C T ;
READ       : R E A D ;
USE        : U S E ;
MANAGE     : M A N A G E ;
ANY_TENANCY : A N Y '-' T E N A N C Y ;

LBRACE : '{' ;
RBRACE : '}' ;
COMMA  : ',' ;
COLON  : ':' ;
DOT    : '.' ;
EQ     : '=' ;
NEQ    : '!=' ;

OCID : 'ocid1.' ([-a-zA-Z0-9.]+) ;

IDENTIFIER  : [a-zA-Z][a-zA-Z0-9_-]* ;
ALL_RESOURCES : A L L '-' R E S O U R C E S ;

STRING : '\'' (~['\r\n\\] | '\\' .)* '\'' ;
// Whole =/pattern/ and !=/pattern/ as single tokens; allow optional whitespace
// before the slash so that both  =/pat/  and  = /pat/  work.
REGEX_MATCH     : '=' [ \t]* '/' (~['/\r\n\\] | '\\' .)* '/' ;
NEQ_REGEX_MATCH : '!=' [ \t]* '/' (~['/\r\n\\] | '\\' .)* '/' ;

WS      : [ \t]+ -> skip ;
NEWLINE : [\r\n]+ -> skip ;
