import re

STACK_BUILDUP_INIT = "ADD R6, R6, -4  ;; Make space for rv, old ra, old fp, lv1 \n" \
                     "STR R5, R6, 1   ;; Store old fp\n"\
                     "STR R7, R6, 2   ;; Store old ra\n"\
                     "ADD R5, R6, 0   ;; Set SP to FP\n\n"\
                     "ADD R6, R6, -5  ;; Make space to save registers\n"

STACK_BUILDUP_STORE_REG = "STR R0, R6, 0\nSTR R1, R6, 1\nSTR R2, R6, 2\nSTR R3, R6, 3\nSTR R4, R6, 4   ;; Save R0,R1,R2,R3,R4 on stack\n"

STACK_TEARDOWN_LOAD_REG = "LDR R0, R6, 0\nLDR R1, R6, 1\nLDR R2, R6, 2\nLDR R3, R6, 3\nLDR R4, R6, 4\nADD R6, R5, 0   ;; Load R0,R1,R2,R3,R4 from stack\n\n"
STACK_TEARDOWN_FINAL = "LDR R5, R6, 1   ;; Load old fp\n" \
                       "LDR R7, R6, 2   ;; Load old ra\n" \
                       "ADD R6, R6, 3   ;; Pop lv1, old fp, old ra\n" \
                       "RET\n"

STACK_IMPL = ""

stack_pointer = 0x6000
args_dict = {}  # Key: Argument name, Value: Offset from R5 (local variable 1)
local_vars_dict = {} # Key: Local variable name, Value: Offset
local_vars_vals_dict = {} # Key: Local variable name, Value: original value
reg_dict = {}

FUNC_NAME = None
NO_OF_ARGS = 0

with open("file.py") as file:
    lines = file.readlines()

    # Parse function name, no.of arguments and no.of local variables used
    for line in lines:

        # Get function name
        if re.search("def \s*", line):
            idx = re.search("def \s*", line).end()
            end_idx = re.search("def [a-x]*", line).end()
            FUNC_NAME = line[idx:end_idx].strip().upper()

        # Get no.of arguments
        if re.search("def\s*[a-z]*\([a-z]", line):
           # print("HERE")
            start_idx = re.search("def [a-z]*\(", line).end()
            line = line[start_idx:]
            line = line.split(")")[0].split(',')
            if not len(line) == 0:
                for idx, arg in enumerate(line):
                    args_dict[arg.strip()] = 4+idx
                NO_OF_ARGS = len(line)
        
        # Find and index local variables
        elif re.search("\s*[a-z]*[^+\-*/]=", line):
            var, val = line.split("=")
            var = var.strip()
            local_vars_dict[var] = len(local_vars_dict.keys())
            local_vars_vals_dict[var] = int(val.strip())

    with open("out.asm", "w") as out:
        
        # STACK BUILDUP

        out.write(f".orig x3000\n{FUNC_NAME}\n")
        out.write(";;STACK BUILDUP\n")
        out.write(STACK_BUILDUP_INIT)
        # Make space for local vars on stack
        for var in range(len(local_vars_dict.keys()) - 1): out.write("ADD R6, R6, -1\n")  
        out.write(STACK_BUILDUP_STORE_REG)
        out.write("\n;;Core functionality\n")

        # Clear all local variable spots
        out.write("AND R0, R0, 0\n")
        for var in local_vars_dict.keys():
           # print(var)
            if local_vars_vals_dict[var]:
                out.write(f"LD R0, {var.upper()}\n")
                out.write(f"STR R0, R5, -{local_vars_dict[var]}\n")
                out.write("AND R0, R0, 0\n")
            else:
                out.write(f"STR R0, R5, -{local_vars_dict[var]}\n")

        # SUBROUTINE IMPLEMENTATION
        in_a_loop, loop_indent = False, 4
        for line in lines:

            current_no_of_indents = re.search("\s*", line).end()
            # Check if there is a while loop
            if re.search("while", line):
                in_a_loop = True
                start_idx = re.search("while\s*\(", line).end()
                loop_condition = line[start_idx:].split(")")[0]
                #print(loop_condition)
                if ">" in loop_condition:

                    var, val = loop_condition.split(">")
                    out.write("\nAND R0, R0, 0\n")
                    var = var.strip()
                    val = val.strip()
                    if val.isnumeric():

                        # Make R0 equal to the condition value
                        temp_val = int(val)
                        while (temp_val > 15):
                            out.write(f"ADD R0, R0, {15}\n")
                            temp_val -= 15
                        out.write(f"ADD R0, R0, {temp_val}  ;; R0 = {val}\n\n")

                        # Start writing while loop initialization
                        out.write("WHILE\n"\
                                  "NOT R1, R0\n"\
                                  f"ADD R1, R1, 1   ;; R1 = -{val}\n"\
                                  f"LDR R2, R5, {local_vars_dict[var]}   ;; R2 = {var}\n"\
                                  f"ADD R1, R1, R2  ;; R1 = {var} - {val}\n"\
                                  "BRnz END\n\n")
   
            # Write Core while loop content
            elif in_a_loop and current_no_of_indents == loop_indent+4:
                expression = line.strip()
                if "-=" in expression:
                    var, val = expression.split("-=")
                    if val.isnumeric():
                        out.write(f"LDR R1, R5, {local_vars_dict[var]}  ;; R1 = {var}\n")
                        out.write(f"AND R2, R2, 0  ;; R2 = 0\n")
                        temp_val = int(val)
                        while (temp_val > 15):
                            out.write(f"ADD R2, R2, {15}\n")
                            temp_val -= 15
                        out.write(f"ADD R2, R2, {temp_val}  ;; R2 = {val}\n")
                        out.write("NOT R2, R2\n")
                        out.write(f"ADD R2, R2, 1  ;; R2 = -{val}\n")
                        out.write(f"ADD R1, R1, R2  ;; R1 = {var} - {val}\n")
                        out.write(f"STR R1, R5, {local_vars_dict[var]}  ;; {var} = R1\n")
            
            elif in_a_loop and current_no_of_indents == loop_indent:
                in_a_loop = False
                out.write("BR WHILE\n\n")
                out.write("END\n")

            # Handle returning the function
            if re.search("return", line):
                return_val = line.split("n")[1].strip()

                # Handle when return value is just a variable
                if return_val.isalpha():
                    if return_val in local_vars_dict:
                        out.write(f"LDR R0, R5, {local_vars_dict[return_val]}\n"\
                                  f"STR R0, R5, 3  ;; rv = {return_val}\n\n")
            
            # TODO: Handle more while conditions >, <, >=, <=, ==, !=
            # TODO: Handle more while terminating conditions (i.e +=, *=, /=)

        # Write STACK TEARDOWN
        out.write(";;STACK TEARDOWN\n")
        out.write(STACK_TEARDOWN_LOAD_REG)
        out.write(STACK_TEARDOWN_FINAL)
        out.write("HALT\n\n")
        # Add .fills for vars with initial values
        for var in local_vars_dict.keys():
            if local_vars_vals_dict[var]:
                out.write(f"{var.upper()} .fill {local_vars_vals_dict[var]}\n")
        out.write(".end")



#################### OLD CODE ########################
# Note from future: I can't understand this code :(((
# # Begin the loop implementation
# if re.search("while", line):
#     in_a_loop = True
#     loop_indent = re.search(""\s*[a-z]"", line).end() + 4
#     var, val = line.split("while ")[1][1:-3].split(">")
#     var = var.strip()
#     val = int(val.strip())
#     if args_dict.get(var, 0):
#         STACK_IMPL += f"AND R0, R0, 0\nLDR R0, R5, {args_dict[var]}\nWHILE\nADD R0,R0,0\nBRnz END  ;; terminating condition\n"
#     else:
#         STACK_IMPL += f"AND R0, R0, 0\nLDR R0, R5, {local_vars_dict[var]}\nWHILE\nADD R0,R0,0\nBRnz END  ;; terminating condition\n"


# # End the loop implementation
# elif in_a_loop and re.search("\s*[a-z]", line) and re.search("\s*[a-z]", line).end() != loop_indent:
#     STACK_IMPL += "ADD R0, R0, -1\nBR WHILE\nEND\n"
#     in_a_loop = False

# elif in_a_loop:
#     # Find and index local variables
#     if re.search("\s*[a-z]*[+]=", line):
#       #  print("WHOA", line)
#         var, val = line.split("=")
#         var = var[:-1].strip()
#         val = val[0]
#         STACK_IMPL += f"LDR R1, R5, {args_dict[val]}\nLDR R2, R5, -{local_vars_dict[var]}\nADD R2, R2, R1\nSTR R2, R5, -{local_vars_dict[var]}\n"

# Write the official core functionality LC-3 ASM code
# out.write(STACK_IMPL)
