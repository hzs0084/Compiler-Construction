import re
import sys

# Read the file

program_lines = []

with open(f"testing_simple_c_programs/test2.c", "r") as program_file:
    program_lines = [line.strip()
                      for line in program_file.read()]

#     print(program_lines)


f = open(f"testing_simple_c_programs/test2.c", "r")
Program = f.read()

#print(Program)


def SpaceRemover(Program):
    scanned_program = []
    for line in Program:
        if (line.strip() != ''):
            scanned_program.append(line.strip())
    #print(scanned_program)
    return scanned_program
    
SpaceRemover(Program)

def CommentRemover(Program):
    program_multi_line_comments_removed = re.sub(r"/\*[^*]*\*+(?:[^/*][^*]*\*+)*/", "", Program) #needs to be interpreted as raw otherwise the terminal throws a syntax warning
    program_single_line_removed  = re.sub("//.*", "", program_multi_line_comments_removed)
    program_comments_removed = program_single_line_removed
    print(program_comments_removed)
    return program_comments_removed

CommentRemover(Program)





# I need to write a function that would ignore the comments


# Save the contents of the file into a new file


# Output the contents that was stored as tokens