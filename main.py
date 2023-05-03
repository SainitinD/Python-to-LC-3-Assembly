import re

STACK_BUILDUP_INIT = "ADD R6, R6, -4  ;; Make space for rv, old ra, old fp, lv1 \n" \
                     "STR R5, R6, 1   ;; Store old fp\n"\
                     "STR R7, R6, 2   ;; Store old ra\n"\
                     "ADD R5, R6, 0   ;; Set SP to FP\n\n"\
                     "ADD R6, R6, -5  ;; Make space to save registers\n"

STACK_BUILDUP_STORE_REG = "STR R0, R6, 0\n" \
                          "STR R1, R6, 1\n" \
                          "STR R2, R6, 2\n" \
                          "STR R3, R6, 3\n" \
                          "STR R4, R6, 4   ;; Save R0,R1,R2,R3,R4 on stack\n"

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
            start_idx = re.search("def [a-z]*\(", line).end()
            line = line[start_idx:]
            line = line.split(")")[0].split(',')
            if not len(line) == 0:
                for idx, arg in enumerate(line):
                    args_dict[arg.strip()] = 4+idx
                NO_OF_ARGS = len(line)
        
        # Find and index local variables
        elif re.search("\s*[a-z]*[^><+\-*/]=", line):
            var, val = line.split("=")
            var = var.strip()
            val = val.strip()
            if var not in local_vars_dict:
                local_vars_dict[var] = len(local_vars_dict.keys())

            # Account for edge case when var equals a function call
            if "(" not in val:
                local_vars_vals_dict[var] = int(val.strip()) if val.isnumeric() else val
            else:
                local_vars_vals_dict[var] = local_vars_vals_dict.get(var, 0)

    # Write the assembly function
    with open("out.asm", "w") as out:
        
        # STACK BUILDUP
        out.write(f".orig x3000\n{FUNC_NAME}\n")
        out.write(";;STACK BUILDUP\n")
        out.write(STACK_BUILDUP_INIT)
        # Make space for local vars on stack
        for var in range(len(local_vars_dict.keys()) - 1): out.write(f"ADD R6, R6, -1  ;; Make space for local variable\n")
        out.write(STACK_BUILDUP_STORE_REG)
        out.write("\n;;Core functionality\n")

        # Clear all local variable spots
       # out.write("AND R0, R0, 0\n")
        for var in local_vars_dict.keys():
           # print(var)
            if local_vars_vals_dict[var]:
                out.write(f"LD R0, {var.upper()}\n")
                out.write(f"STR R0, R5, -{local_vars_dict[var]}  ;; storing local var\n")
                #out.write("AND R0, R0, 0\n")
            else:
                out.write("AND R0, R0, 0\n")
                out.write(f"STR R0, R5, -{local_vars_dict[var]}  ;; clearing local var\n")

        # SUBROUTINE IMPLEMENTATION
        in_a_loop, loop_indent, store_ans_in_mem = False, 4, False
        for line in lines:
            current_no_of_indents = re.search("\s*", line).end()
            # Check if there is a while loop
            if re.search("while", line):
                in_a_loop = True
                start_idx = re.search("while\s*\(", line).end()
                loop_condition = line[start_idx:].split(")")[0]
                #print(loop_condition)
                if ">" in loop_condition or "<" in loop_condition:
                    sign = ">" if ">" in loop_condition else "<"
                    sign = sign+"=" if "=" in loop_condition else sign
                    var, val = loop_condition.split(sign)
                    out.write("\nAND R0, R0, 0\n")
                    var = var.strip()
                    val = val.strip()

                    # Handle when condition is a number
                    if val.isnumeric():
                        var_off = local_vars_dict[var] if var in local_vars_dict else args_dict[var]

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
                                  f"LDR R2, R5, {var_off}   ;; R2 = {var}\n"\
                                  f"ADD R1, R1, R2  ;; R1 = {var} - {val}\n")

                    # Handle when condition has a variable
                    elif val.isalpha():
                        var_off = local_vars_dict[var] if var in local_vars_dict else args_dict[var]
                        val_off = local_vars_dict[val] if val in local_vars_dict else args_dict[val]
                        # Start writing while loop initialization
                        out.write("WHILE\n")
                        if var in local_vars_dict:
                            out.write(f"LDR R0, R5, -{var_off}  ;; R0 = {var}\n")
                        else:
                            out.write(f"LDR R0, R5, {var_off}  ;; R0 = {var}\n")
                        if val in local_vars_dict:
                            out.write(f"LDR R1, R5, -{val_off}  ;; R1 = {val}\n")
                        else:
                            out.write(f"LDR R1, R5, {val_off}  ;; R1 = {val}\n")

                        out.write("NOT R1, R1\n"\
                                  f"ADD R1, R1, 1  ;; R1 = -{val}\n"\
                                  f"ADD R0, R0, R1  ;; R0 = {var} - {val}\n")

                    if ">" in sign:
                        if "=" in loop_condition:
                            out.write("BRn END\n")
                        else:
                            out.write("BRnz END\n")
                    else:
                        if "=" in loop_condition:
                            out.write("BRp END\n")
                        else:
                            out.write("BRzp END\n")

            # Write Core while loop content
            elif in_a_loop and current_no_of_indents == loop_indent+4:
                expression = line.strip()
                if "-=" in expression:
                    #print("HERE")
                    var, val = expression.split("-=")
                    var = var.strip()
                    val = val.strip()
                    var_off = local_vars_dict[var] if var in local_vars_dict else args_dict[var]
                    if val.isnumeric():
                        if var in local_vars_dict:
                            out.write(f"LDR R1, R5, -{var_off}  ;; R1 = {var}\n")
                        else:
                            out.write(f"LDR R1, R5, {var_off}  ;; R1 = {var}\n")
                        out.write(f"AND R2, R2, 0  ;; R2 = 0\n")
                        temp_val = int(val)
                        while (temp_val > 15):
                            out.write(f"ADD R2, R2, {15}\n")
                            temp_val -= 15
                        out.write(f"ADD R2, R2, {temp_val}  ;; R2 = {val}\n")
                        out.write("NOT R2, R2\n")
                        out.write(f"ADD R2, R2, 1  ;; R2 = -{val}\n")
                        out.write(f"ADD R1, R1, R2  ;; R1 = {var} - {val}\n")
                        if var in local_vars_dict:
                            out.write(f"STR R1, R5, -{var_off}  ;; {var} = R1\n")
                        else:
                            # THIS PROBABLY SHOUDLN'T BE ACCESSED. BUT IM ADDING IT JUST IN CASE
                            out.write(f"STR R1, R5, {var_off}  ;; {var} = R1\n")
                    elif val.isalpha():
                        val_off = local_vars_dict[val] if val in local_vars_dict else args_dict[val]
                        out.write(f"LDR R1, R5, -{var_off}  ;; R1 = {var}\n")
                        if val in local_vars_dict:
                            out.write(f"LDR R2, R5, -{val_off}  ;; R2 = {val}\n")
                        else:
                            out.write(f"LDR R2, R5, {val_off}  ;; R2 = {val}\n")
                        out.write("NOT R2, R2\n")
                        out.write(f"ADD R2, R2, 1  ;; R2 = -{val}\n")
                        out.write(f"ADD R1, R1, R2  ;; R1 = {var} - {val}\n")
                        if var in local_vars_dict:
                            out.write(f"STR R1, R5, -{var_off}  ;; {var} = R1\n")
                        else:
                            # THIS PROBABLY SHOUDLN'T BE ACCESSED. BUT IM ADDING IT JUST IN CASE
                            out.write(f"STR R1, R5, {var_off}  ;; {var} = R1\n")



                elif "+=" in expression:
                    var, val = expression.split("+=")
                    var = var.strip()
                    val = val.strip()
                    var_off = local_vars_dict[var] if var in local_vars_dict else args_dict[var]
                    if val.isnumeric():
                        if var in local_vars_dict:
                            out.write(f"LDR R1, R5, -{var_off}  ;; R1 = {var}\n")
                        else:
                            out.write(f"LDR R1, R5, {var_off}  ;; R1 = {var}\n")
                        out.write(f"AND R2, R2, 0  ;; R2 = 0\n")
                        temp_val = int(val)
                        while (temp_val > 15):
                            out.write(f"ADD R2, R2, {15}\n")
                            temp_val -= 15
                        out.write(f"ADD R2, R2, {temp_val}  ;; R2 = {val}\n")
                        out.write(f"ADD R1, R1, R2  ;; R1 = {var} + {val}\n")
                        if var in local_vars_dict:
                            out.write(f"STR R1, R5, -{var_off}  ;; {var} = R1\n")
                        else:
                            # THIS PROBABLY SHOUDLN'T BE ACCESSED. BUT IM ADDING IT JUST IN CASE
                            out.write(f"STR R1, R5, {var_off}  ;; {var} = R1\n")
                    elif val.isalpha():
                        val_off = local_vars_dict[val] if val in local_vars_dict else args_dict[val]
                        if var in local_vars_dict:
                            out.write(f"LDR R1, R5, -{var_off}  ;; R1 = {var}\n")
                        else:
                            out.write(f"LDR R1, R5, {var_off}  ;; R1 = {var}\n")
                        if val in local_vars_dict:
                            out.write(f"LDR R2, R5, -{val_off}  ;; R2 = {val}\n")
                        else:
                            out.write(f"LDR R2, R5, {val_off}  ;; R2 = {val}\n")
                        out.write(f"ADD R1, R1, R2  ;; R1 = {var} + {val}\n")
                        if var in local_vars_dict:
                            out.write(f"STR R1, R5, -{var_off}  ;; {var} = R1\n")
                        else:
                            # THIS PROBABLY SHOUDLN'T BE ACCESSED. BUT IM ADDING IT JUST IN CASE
                            out.write(f"STR R1, R5, {var_off}  ;; {var} = R1\n")

                elif "=" in expression:
                    var, val = expression.split("=")
                    var = var.strip()
                    val = val.strip()
                    var_off = local_vars_dict[var] if var in local_vars_dict else args_dict[var]
                    if val.isnumeric():
                        if var in local_vars_dict:
                            out.write(f"LDR R1, R5, -{var_off}  ;; R1 = {var}\n")
                        else:
                            out.write(f"LDR R1, R5, {var_off}  ;; R1 = {var}\n")
                        out.write(f"AND R2, R2, 0  ;; R2 = 0\n")
                        temp_val = int(val)
                        while (temp_val > 15):
                            out.write(f"ADD R2, R2, {15}\n")
                            temp_val -= 15
                        out.write(f"ADD R2, R2, {temp_val}  ;; R2 = {val}\n")
                        out.write(f"STR R2, R5, {var_off}  ;; {var} = R2\n")
                    elif "(" in val:
                        callee_func_name, args = val[:-1].split("(")
                        callee_func_name = callee_func_name.upper()
                        args = args.split(",")
                        out.write(f"ADD R6, R6, -2  ;; Make space for {callee_func_name} args\n")
                        for idx, arg in enumerate(args):
                            arg = arg.strip()
                            arg_off = local_vars_dict[arg] if arg in local_vars_dict else args_dict[arg]
                            out.write(f"LDR R2, R5, -{arg_off}  ;; R2 = {arg}\n"
                                      f"STR R2, R6, {idx}  ;; Store {arg} on stack\n")
                        out.write(f"JSR {callee_func_name}\n"
                                  f"LDR R2, R6, 0  ;; R2 = {val}\n"
                                  f"ADD R6, R6, {len(args) + 1}  ;; pop rv, callee args\n")
                        if var in local_vars_dict:
                            out.write(f"STR R2, R5, -{var_off}  ;; {var} = {val}\n")
                        else:
                            out.write(f"STR R2, R5, {var_off}  ;; {var} = {val}\n")
                    elif val.isalpha():
                        val_off = local_vars_dict[val] if val in local_vars_dict else args_dict[val]
                        if var in local_vars_dict:
                            out.write(f"LDR R1, R5, -{var_off}  ;; R1 = {var}\n")
                        else:
                            out.write(f"LDR R1, R5, {var_off}  ;; R1 = {var}\n")
                        if val in local_vars_dict:
                            out.write(f"LDR R2, R5, -{val_off}  ;; R2 = {val}\n")
                        else:
                            out.write(f"LDR R2, R5, {val_off}  ;; R2 = {val}\n")
                        out.write(f"STR R2, R5, {var_off}  ;; {var} = R2\n")
            
            elif in_a_loop and current_no_of_indents == loop_indent:
                in_a_loop = False
                out.write("BR WHILE  ;; End of Loop\n\n")
                out.write("END\n")
            else:
                expression = line.strip()
                if "-=" in expression:
                    # print("HERE")
                    var, val = expression.split("-=")
                    var = var.strip()
                    val = val.strip()
                    var_off = local_vars_dict[var] if var in local_vars_dict else args_dict[var]
                    if val.isnumeric():
                        if var in local_vars_dict:
                            out.write(f"LDR R1, R5, -{var_off}  ;; R1 = {var}\n")
                        else:
                            out.write(f"LDR R1, R5, {var_off}  ;; R1 = {var}\n")
                        out.write(f"AND R2, R2, 0  ;; R2 = 0\n")
                        temp_val = int(val)
                        while (temp_val > 15):
                            out.write(f"ADD R2, R2, {15}\n")
                            temp_val -= 15
                        out.write(f"ADD R2, R2, {temp_val}  ;; R2 = {val}\n")
                        out.write("NOT R2, R2\n")
                        out.write(f"ADD R2, R2, 1  ;; R2 = -{val}\n")
                        out.write(f"ADD R1, R1, R2  ;; R1 = {var} - {val}\n")
                        if var in local_vars_dict:
                            out.write(f"STR R1, R5, -{var_off}  ;; {var} = R1\n")
                        else:
                            # THIS PROBABLY SHOUDLN'T BE ACCESSED. BUT IM ADDING IT JUST IN CASE
                            out.write(f"STR R1, R5, {var_off}  ;; {var} = R1\n")
                    elif val.isalpha():
                        val_off = local_vars_dict[val] if val in local_vars_dict else args_dict[val]
                        out.write(f"LDR R1, R5, -{var_off}  ;; R1 = {var}\n")
                        if val in local_vars_dict:
                            out.write(f"LDR R2, R5, -{val_off}  ;; R2 = {val}\n")
                        else:
                            out.write(f"LDR R2, R5, {val_off}  ;; R2 = {val}\n")
                        out.write("NOT R2, R2\n")
                        out.write(f"ADD R2, R2, 1  ;; R2 = -{val}\n")
                        out.write(f"ADD R1, R1, R2  ;; R1 = {var} - {val}\n")
                        if var in local_vars_dict:
                            out.write(f"STR R1, R5, -{var_off}  ;; {var} = R1\n")
                        else:
                            # THIS PROBABLY SHOUDLN'T BE ACCESSED. BUT IM ADDING IT JUST IN CASE
                            out.write(f"STR R1, R5, {var_off}  ;; {var} = R1\n")



                elif "+=" in expression:
                    var, val = expression.split("+=")
                    var = var.strip()
                    val = val.strip()
                    var_off = local_vars_dict[var] if var in local_vars_dict else args_dict[var]
                    if val.isnumeric():
                        if var in local_vars_dict:
                            out.write(f"LDR R1, R5, -{var_off}  ;; R1 = {var}\n")
                        else:
                            out.write(f"LDR R1, R5, {var_off}  ;; R1 = {var}\n")
                        out.write(f"AND R2, R2, 0  ;; R2 = 0\n")
                        temp_val = int(val)
                        while (temp_val > 15):
                            out.write(f"ADD R2, R2, {15}\n")
                            temp_val -= 15
                        out.write(f"ADD R2, R2, {temp_val}  ;; R2 = {val}\n")
                        out.write(f"ADD R1, R1, R2  ;; R1 = {var} + {val}\n")
                        if var in local_vars_dict:
                            out.write(f"STR R1, R5, -{var_off}  ;; {var} = R1\n")
                        else:
                            # THIS PROBABLY SHOUDLN'T BE ACCESSED. BUT IM ADDING IT JUST IN CASE
                            out.write(f"STR R1, R5, {var_off}  ;; {var} = R1\n")
                    elif val.isalpha():
                        val_off = local_vars_dict[val] if val in local_vars_dict else args_dict[val]
                        if var in local_vars_dict:
                            out.write(f"LDR R1, R5, -{var_off}  ;; R1 = {var}\n")
                        else:
                            out.write(f"LDR R1, R5, {var_off}  ;; R1 = {var}\n")
                        if val in local_vars_dict:
                            out.write(f"LDR R2, R5, -{val_off}  ;; R2 = {val}\n")
                        else:
                            out.write(f"LDR R2, R5, {val_off}  ;; R2 = {val}\n")
                        out.write(f"ADD R1, R1, R2  ;; R1 = {var} + {val}\n")
                        if var in local_vars_dict:
                            out.write(f"STR R1, R5, -{var_off}  ;; {var} = R1\n")
                        else:
                            # THIS PROBABLY SHOUDLN'T BE ACCESSED. BUT IM ADDING IT JUST IN CASE
                            out.write(f"STR R1, R5, {var_off}  ;; {var} = R1\n")

                elif "=" in expression:
                    var, val = expression.split("=")
                    var = var.strip()
                    val = val.strip()
                    var_off = local_vars_dict[var] if var in local_vars_dict else args_dict[var]
                    if val.isnumeric():
                        if var in local_vars_dict:
                            out.write(f"LDR R1, R5, -{var_off}  ;; R1 = {var}\n")
                        else:
                            out.write(f"LDR R1, R5, {var_off}  ;; R1 = {var}\n")
                        out.write(f"AND R2, R2, 0  ;; R2 = 0\n")
                        temp_val = int(val)
                        while (temp_val > 15):
                            out.write(f"ADD R2, R2, {15}\n")
                            temp_val -= 15
                        out.write(f"ADD R2, R2, {temp_val}  ;; R2 = {val}\n")
                        out.write(f"STR R2, R5, {var_off}  ;; {var} = R2\n")
                    elif "(" in val:
                        callee_func_name, args = val[:-1].split("(")
                        callee_func_name = callee_func_name.upper()
                        args = args.split(",")
                        out.write(f"ADD R6, R6, -2  ;; Make space for {callee_func_name} args\n")
                        for idx, arg in enumerate(args):
                            arg = arg.strip()
                            arg_off = local_vars_dict[arg] if arg in local_vars_dict else args_dict[arg]
                            out.write(f"LDR R2, R5, -{arg_off}  ;; R2 = {arg}\n"
                                      f"STR R2, R6, {idx}  ;; Store {arg} on stack\n")
                        out.write(f"JSR {callee_func_name}\n"
                                  f"LDR R2, R6, 0  ;; R2 = {val}\n"
                                  f"ADD R6, R6, {len(args) + 1}  ;; pop rv, callee args\n")
                        if var in local_vars_dict:
                            out.write(f"STR R2, R5, -{var_off}  ;; {var} = {val}\n")
                        else:
                            out.write(f"STR R2, R5, {var_off}  ;; {var} = {val}\n")
                    elif val.isalpha():
                        val_off = local_vars_dict[val] if val in local_vars_dict else args_dict[val]
                        if var in local_vars_dict:
                            out.write(f"LDR R1, R5, -{var_off}  ;; R1 = {var}\n")
                        else:
                            out.write(f"LDR R1, R5, {var_off}  ;; R1 = {var}\n")
                        if val in local_vars_dict:
                            out.write(f"LDR R2, R5, -{val_off}  ;; R2 = {val}\n")
                        else:
                            out.write(f"LDR R2, R5, {val_off}  ;; R2 = {val}\n")
                        out.write(f"STR R2, R5, {var_off}  ;; {var} = R2\n")


            # Handle returning the function
            if re.search("return", line):
                return_val = line.split("n")[1].strip()

                # Handle when return value is just a variable
                if return_val.isalpha():
                    if return_val in local_vars_dict:
                        out.write(f"LDR R0, R5, {local_vars_dict[return_val]}\n"\
                                  f"STR R0, R5, 3  ;; rv = {return_val}\n\n")
                    elif return_val in args_dict:
                        out.write(f"LDR R0, R5, {args_dict[return_val]}\n"\
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
            if type(local_vars_vals_dict[var]) == int:
                out.write(f"{var.upper()} .fill {local_vars_vals_dict[var]}\n")
            elif "(" not in val:
                var_name = local_vars_vals_dict[var]
                val = local_vars_dict[var_name] if var_name in local_vars_dict else args_dict[var_name]
                out.write(f"{var.upper()} .fill {val}\n")
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
