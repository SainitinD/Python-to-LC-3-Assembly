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
            print("HERE")
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
            print(var)
            if local_vars_vals_dict[var]:
                out.write(f"LD R0, {var.upper()}\n")
                out.write(f"STR R0, R5, -{local_vars_dict[var]}\n")
                out.write("AND R0, R0, 0\n")
            else:
                out.write(f"STR R0, R5, -{local_vars_dict[var]}\n")

        #LD R0, LABEL

       # LABEL .fill VAL

        # SUBROUTINE IMPLEMENTATION
        inALoop, loop_indent = False, 4
        for line in lines:
            
            # Begin the loop implementation
            if re.search("while", line):
                inALoop = True
                loop_indent = re.search("\s*[a-z]", line).end() + 4
                var, val = line.split("while ")[1][1:-3].split(">")
                STACK_IMPL += f"AND R0, R0, 0\nLDR R0, R5, {args_dict[var]}\nWHILE\nADD R0,R0,0\nBRnz END  ;; terminating condition\n"

            # End the loop implementation
            elif inALoop and re.search("\s*[a-z]", line) and re.search("\s*[a-z]", line).end() != loop_indent:
                STACK_IMPL += "ADD R0, R0, -1\nBR WHILE\nEND\n"
                inALoop = False
            
            elif inALoop:
                # Find and index local variables
                if re.search("\s*[a-z]*[+]=", line):
                  #  print("WHOA", line)
                    var, val = line.split("=")
                    var = var[:-1].lstrip()
                    val = val[0]
                    STACK_IMPL += f"LDR R1, R5, {args_dict[val]}\nLDR R2, R5, -{local_vars_dict[var]}\nADD R2, R2, R1\nSTR R2, R5, -{local_vars_dict[var]}\n"

            # Handle returning the function
            if re.search("return", line):
                var = line.split("n ")[1].strip()
                if var in local_vars_dict:
                    STACK_IMPL += f"LDR R0, R5, {local_vars_dict[var]}\nSTR R0, R5, 3\n"
        
        # Write the official core functionality LC-3 ASM code
        out.write(STACK_IMPL)
        out.write("\n")

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

    # print(lines)
