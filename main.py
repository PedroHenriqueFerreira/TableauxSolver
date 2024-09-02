from lark import Lark, Transformer

from collections import deque
from sys import argv

TOKEN_OR = "|"
TOKEN_AND = "&"
TOKEN_IMPL = "->"
TOKEN_NEG = "¬"

TOKEN_ATOM = "atom"

grammar = """
    start: expr

    ?expr: "("expr "{TOKEN_OR}" expr ")"  -> or_
          | "("expr "{TOKEN_AND}" expr ")"  -> and_
          | "("expr "{TOKEN_IMPL}" expr ")"  -> impl_
          | "{TOKEN_NEG}" expr  -> not_
          | VAR

    VAR: /[a-z]+[_0-9]*/

""".format(TOKEN_OR=TOKEN_OR, TOKEN_AND=TOKEN_AND, TOKEN_IMPL=TOKEN_IMPL, TOKEN_NEG=TOKEN_NEG)

# print(grammar)

parser = Lark(grammar, start='start')

class SubformulaExtractor(Transformer):
    def __init__(self):
        self.main_conective = None
        self.immediate_subformulas = None

    def or_(self, args):
        self.main_conective = TOKEN_OR
        self.immediate_subformulas = [args[0], args[1]]
        return f"({args[0]}{TOKEN_OR}{args[1]})"

    def and_(self, args):
        self.main_conective = TOKEN_AND
        self.immediate_subformulas = [args[0], args[1]]
        return f"({args[0]}{TOKEN_AND}{args[1]})"

    def impl_(self, args):
        self.main_conective = TOKEN_IMPL
        self.immediate_subformulas = [args[0], args[1]]
        return f"({args[0]}{TOKEN_IMPL}{args[1]})"

    def not_(self, args):
        self.main_conective = TOKEN_NEG
        self.immediate_subformulas = [args[0]]
        return f"{TOKEN_NEG}{args[0]}"

    def VAR(self, token):
        self.main_conective = TOKEN_ATOM
        self.immediate_subformulas = [token.value]
        return token.value

    def start(self, args):
        return args[0]

class PropositionalFormula:
    @staticmethod
    def _get_parsed_formula(formula):
        try:
          parse_tree = parser.parse(formula)
        except:
          return
        return parse_tree

    @staticmethod
    def get_main_conective_and_immediate_subformulas(formula):
      parse_tree = PropositionalFormula._get_parsed_formula(formula)
      if parse_tree is None:
        return None, None
      extractor = SubformulaExtractor()
      extractor.transform(parse_tree)
      return extractor.main_conective, extractor.immediate_subformulas

#EXEMPLO DE USO
# conective, subformulas = PropositionalFormula.get_main_conective_and_immediate_subformulas("((a&b)->c)")

# if conective is not None:
#   print("valida")
#   print(conective, subformulas)
# else:
#   print("malformulada")

# Código do aluno

class MarkedFormula:
    ''' Classe que realiza as operações da fórmula '''
    
    def __init__(self, mark: bool, formula: str):
        self.mark = mark
        self.formula = formula
        
        self.is_beta = self.get_is_beta()
        self.is_atom = self.get_is_atom()

    def __repr__(self):
        ''' Representação da fórmula '''
        
        return f'{["F", "T"][self.mark]}{self.formula}'

    def __len__(self):
        ''' Retorna o tamanho da string referente a fórmula '''

        return len(self.formula)

    def __eq__(self, other: 'MarkedFormula'):
        ''' Verifica se uma fórmula é diferente de outra '''
        
        return self.mark == other.mark and self.formula == other.formula

    def __ne__(self, other: 'MarkedFormula'):
        ''' Veririca se uma fórmula é igual a outra '''
        
        return not self == other

    def get_is_atom(self):
        ''' Retorna se a fórmula é um átomo '''
        
        conective, _ = PropositionalFormula.get_main_conective_and_immediate_subformulas(self.formula)

        if conective == TOKEN_ATOM:
            return True

        return False

    def get_is_beta(self):
        ''' Retorna se a fórmula é do tipo beta '''
        
        conective, _ = PropositionalFormula.get_main_conective_and_immediate_subformulas(self.formula)

        if (self.mark and conective in (TOKEN_OR, TOKEN_IMPL)) or (not self.mark and conective == TOKEN_AND):
            return True

        return False

    def conjugate(self):
        ''' Retorna o conjugado de uma fórmula '''
        
        return MarkedFormula(not self.mark, self.formula)

    def expand(self):
        ''' Expande a fórmula fazendo a devida marcação dependendo do tipo de fórmula '''
        
        conective, subformulas = PropositionalFormula.get_main_conective_and_immediate_subformulas(self.formula)

        if conective is None and subformulas is None:
            raise ValueError('Formato inválido')

        if conective in (TOKEN_OR, TOKEN_AND):
            return [MarkedFormula(self.mark, subformula) for subformula in subformulas]
        elif conective == TOKEN_NEG:
            return [MarkedFormula(not self.mark, subformula) for subformula in subformulas]
        elif conective == TOKEN_IMPL:
            return [MarkedFormula(not self.mark, subformulas[0]), MarkedFormula(self.mark, subformulas[1])]

        return [None]

class Tableuax:
    ''' Classe que realiza as operações do tableaux '''
    
    def __init__(self, file: str):
        self.file = file
        
        self.premisses, self.conclusion = self.get_premisses_conclusion()
        
        self.branch: list[MarkedFormula] = []
        
        self.betas: list[bool] = []
        
        self.stack: deque[tuple[MarkedFormula, int, list[bool]]] = deque()
    
    def get_premisses_conclusion(self):
        ''' Busca as premissas e a conclusão a partir do arquivo de entrada '''
        
        try:
            with open(self.file) as f:
                lines = list(map(lambda x: x.strip(), f.readlines()))

                n = int(lines[0])

                return lines[1:n], lines[-1]
        except:
            raise ValueError('Arquivo de entrada inválido')
    
    def is_closed(self):
        ''' Checa se existe a presença de um átomo e seu conjugado no ramo principal '''
        
        for marked_formula in self.branch:
            if marked_formula.is_atom and marked_formula.conjugate() in self.branch:
                return True
        
        return False
    
    def expand_alphas(self):
        ''' Expande todos os alfas do ramo principal '''
        
        index = 0
        
        while index < len(self.branch):
            marked_formula = self.branch[index]
            
            if self.betas[index] or marked_formula.is_atom or marked_formula.is_beta:
                index += 1
                
                continue
            
            for new_formula in marked_formula.expand():
                self.branch.append(new_formula)
                self.betas.append(new_formula.is_beta)
            
            del self.branch[index]
            del self.betas[index]
    
    def expand_beta(self):
        ''' Expande um dos betas disponíveis no ramo principal '''
        
        # Extrair melhor beta (beta que possui menor fórmula)
        
        index = self.betas.index(True)
        
        for i, (marked_formula, beta) in enumerate(zip(self.branch, self.betas)):
            if beta and len(marked_formula) < len(self.branch[index]):
                index = i
        
        self.betas[index] = False
        
        marked_formula = self.branch[index]
        
        subformula_1, subformula_2 = marked_formula.expand()
        
        self.stack.append((subformula_2, len(self.branch), self.betas[:]))
        
        self.branch.append(subformula_1)
        self.betas.append(subformula_1.is_beta)
    
    def run(self, verbose: bool = False):
        ''' O algoritmo é executado e retorna uma saída '''
        
        # Cria ramo inicial
        
        for premisse in self.premisses:
            premisse_formula = MarkedFormula(True, premisse)
            
            self.branch.append(premisse_formula)
            self.betas.append(premisse_formula.is_beta)
            
        conclusion_formula = MarkedFormula(False, self.conclusion)
            
        self.branch.append(conclusion_formula)
        self.betas.append(conclusion_formula.is_beta)
        
        # Expandir alphas iniciais
        
        self.expand_alphas()
        
        while True:
            if verbose:
                print(f'RAMO: {self.branch}')
                print(f'BETAS: {self.betas}')
                print(f'PILHA: {self.stack}')
                print(f'FECHADO: {self.is_closed()}')
                print('-' * 50)
            
            if self.is_closed():
                if len(self.stack) == 0:
                    return 'Sequente Válido'
                else:
                    subformula, size, betas = self.stack.pop()
                
                    self.branch = self.branch[:size] + [subformula]
                    self.betas = betas[:size] + [subformula.is_beta]
                    
                    self.expand_alphas()
                
            elif True not in self.betas:
                return ' '.join(set(str(formula) for formula in self.branch if formula.is_atom))
            else:
                self.expand_beta()
                self.expand_alphas()

if len(argv) < 2 or '.tab' not in argv[1]:
    raise ValueError('O programa necessita de um arquivo de entrada .tab')
    
print(f'SAÍDA: {Tableuax(argv[1]).run()}')