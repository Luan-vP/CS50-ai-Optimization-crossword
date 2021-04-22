import sys

from crossword import *


class CrosswordCreator():

    def __init__(self, crossword):
        """
        Create new CSP crossword generate.
        """
        self.crossword = crossword
        self.domains = {
            var: self.crossword.words.copy()
            for var in self.crossword.variables
        }

    def letter_grid(self, assignment):
        """
        Return 2D array representing a given assignment.
        """
        letters = [
            [None for _ in range(self.crossword.width)]
            for _ in range(self.crossword.height)
        ]
        for variable, word in assignment.items():
            direction = variable.direction
            for k in range(len(word)):
                i = variable.i + (k if direction == Variable.DOWN else 0)
                j = variable.j + (k if direction == Variable.ACROSS else 0)
                letters[i][j] = word[k]
        return letters

    def print(self, assignment):
        """
        Print crossword assignment to the terminal.
        """
        letters = self.letter_grid(assignment)
        for i in range(self.crossword.height):
            for j in range(self.crossword.width):
                if self.crossword.structure[i][j]:
                    print(letters[i][j] or " ", end="")
                else:
                    print("█", end="")
            print()

    def save(self, assignment, filename):
        """
        Save crossword assignment to an image file.
        """
        from PIL import Image, ImageDraw, ImageFont
        cell_size = 100
        cell_border = 2
        interior_size = cell_size - 2 * cell_border
        letters = self.letter_grid(assignment)

        # Create a blank canvas
        img = Image.new(
            "RGBA",
            (self.crossword.width * cell_size,
             self.crossword.height * cell_size),
            "black"
        )
        font = ImageFont.truetype("assets/fonts/OpenSans-Regular.ttf", 80)
        draw = ImageDraw.Draw(img)

        for i in range(self.crossword.height):
            for j in range(self.crossword.width):

                rect = [
                    (j * cell_size + cell_border,
                     i * cell_size + cell_border),
                    ((j + 1) * cell_size - cell_border,
                     (i + 1) * cell_size - cell_border)
                ]
                if self.crossword.structure[i][j]:
                    draw.rectangle(rect, fill="white")
                    if letters[i][j]:
                        w, h = draw.textsize(letters[i][j], font=font)
                        draw.text(
                            (rect[0][0] + ((interior_size - w) / 2),
                             rect[0][1] + ((interior_size - h) / 2) - 10),
                            letters[i][j], fill="black", font=font
                        )

        img.save(filename)

    def solve(self):
        """
        Enforce node and arc consistency, and then solve the CSP.
        """
        self.enforce_node_consistency()
        self.ac3()
        return self.backtrack(dict())

    def enforce_node_consistency(self):
        """
        Update `self.domains` such that each variable is node-consistent.
        (Remove any values that are inconsistent with a variable's unary
         constraints; in this case, the length of the word.)
        """
        # Make consistent with unary constraints
        for variable in self.domains:
            for word in self.domains[variable].copy():
                if len(word) != variable.length:
                    self.domains[variable].remove(word)

    def revise(self, x, y):
        """
        Make variable `x` arc consistent with variable `y`.
        To do so, remove values from `self.domains[x]` for which there is no
        possible corresponding value for `y` in `self.domains[y]`.

        Return True if a revision was made to the domain of `x`; return
        False if no revision was made.
        """

        revised = False
        
        if self.crossword.overlaps[(x,y)] is None:
            return revised
        
        i,j = self.crossword.overlaps[(x,y)]
        
        for X in self.domains[x].copy():
            # if no value in Y that satisfies binary constraint
            # checking overlap
            valid_option_found = False

            for Y in self.domains[y]:
                if X[i] == Y[j] and X != Y:
                    valid_option_found = True
            
            if not valid_option_found:
                self.domains[x].remove(X)
                revised = True

        return revised

    def ac3(self, arcs=None):
        """
        Update `self.domains` such that each variable is arc consistent.
        If `arcs` is None, begin with initial list of all arcs in the problem.
        Otherwise, use `arcs` as the initial list of arcs to make consistent.

        Return True if arc consistency is enforced and no domains are empty;
        return False if one or more domains end up empty.
        """
        if arcs == None:
            arcs = []
            for pair in self.crossword.overlaps.keys():
                if self.crossword.overlaps[pair] is not None:
                    arcs.append(pair)

        while len(arcs) > 0:
            arc = arcs.pop(0)
            x, y = arc
            # import pdb; pdb.set_trace()
            if self.revise(x, y):
                if len(self.domains[x]) == 0: # if size of X.domain == 0
                    return False
                for z in (self.crossword.neighbors(x) - {y}):
                    arcs.append((z,x))
        
        return True

    def assignment_complete(self, assignment):
        """
        Return True if `assignment` is complete (i.e., assigns a value to each
        crossword variable); return False otherwise.
        """
        return len(assignment) == len(self.crossword.variables)

    def consistent(self, assignment):
        """
        Return True if `assignment` is consistent (i.e., words fit in crossword
        puzzle without conflicting characters); return False otherwise.
        """

        for variable in assignment:
            # Check Unary constraint
            if len(assignment[variable]) != variable.length:
                return False
            
            for neighbour in self.crossword.neighbors(variable):
                overlap = self.crossword.overlaps[variable, neighbour]
                if overlap is None or neighbour not in assignment:
                    continue

                if assignment[variable][overlap[0]] != assignment[neighbour][overlap[1]]:
                    return False

        return True

    def order_domain_values(self, var, assignment):
        """
        Return a list of values in the domain of `var`, in order by
        the number of values they rule out for neighboring variables.
        The first value in the list, for example, should be the one
        that rules out the fewest values among the neighbors of `var`.
        """
        domain = self.domains[var]
        removed_choices_dict = {}

        for value in domain:
            removed_choices = []
            for neighbour in self.crossword.neighbors(var):
                
                # Only unassigned neighbours
                if neighbour in assignment.keys():
                    continue
                
                overlap = self.crossword.overlaps[var,neighbour]
                if len(value) < overlap[0] + 1:
                        continue
                
                for choice in self.domains[neighbour]:
                    if choice == value:
                        removed_choices.append(choice)
                    elif value[overlap[0]] != choice[overlap[1]]:
                        removed_choices.append(choice)

            removed_choices_dict[value] = len(removed_choices)

        sorted_domain = list(domain)
        sorted_domain.sort(key= lambda x: removed_choices_dict[x])

        return sorted_domain

    def select_unassigned_variable(self, assignment):
        """
        Return an unassigned variable not already part of `assignment`.
        Choose the variable with the minimum number of remaining values
        in its domain. If there is a tie, choose the variable with the highest
        degree. If there is a tie, any of the tied variables are acceptable
        return values.
        """
        unassigned = []
        for variable in self.crossword.variables:
            if variable not in assignment.keys():
                unassigned.append(variable)

        if len(unassigned) == 1:
            return unassigned[0]
        elif len(unassigned) == 0:
            return None

        unassigned.sort(key= lambda x: len(self.domains[x]))
        min_domain_length = len(self.domains[unassigned[0]])
        tied = []

        if len(self.domains[unassigned[1]]) != min_domain_length:
            return unassigned[0]
        else:
            for variable in unassigned:
                if len(self.domains[variable]) == min_domain_length:
                    tied.append(variable)

        tied.sort(key=lambda x: len(self.crossword.neighbors(x)))
        return tied[0]

    def backtrack(self, assignment):
        """
        Using Backtracking Search, take as input a partial assignment for the
        crossword and return a complete assignment if possible to do so.

        `assignment` is a mapping from variables (keys) to words (values).

        If no assignment is possible, return None.
        """

        if self.assignment_complete(assignment): 
            return assignment

        variable = self.select_unassigned_variable(assignment)

        for word in self.domains[variable]:


            # Try word
            assignment[variable] = word

            if self.consistent(assignment):
                result = self.backtrack(assignment)

                if result != "failure":
                    return result

            # Remove choice from assignment
            assignment.pop(variable)

        return "failure"


def main():

    # Check usage
    if len(sys.argv) not in [3, 4]:
        sys.exit("Usage: python generate.py structure words [output]")

    # Parse command-line arguments
    structure = sys.argv[1]
    words = sys.argv[2]
    output = sys.argv[3] if len(sys.argv) == 4 else None

    # Generate crossword
    crossword = Crossword(structure, words)
    creator = CrosswordCreator(crossword)
    creator.enforce_node_consistency()
    creator.order_domain_values(list(creator.crossword.variables)[0], {})
    assignment = creator.solve()

    # Print result
    if assignment is None:
        print("No solution.")
    else:
        creator.print(assignment)
        if output:
            creator.save(assignment, output)


if __name__ == "__main__":
    main()
