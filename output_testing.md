program_lines = []

with open(f"testing_simple_c_programs/hello_world.c", "r") as program_file:
    program_lines = [line.strip()
                      for line in program_file.read()]

    print(program_lines)

'''
Output: ['i', 'n', 't', '', 'm', 'a', 'i', 'n', '(', ')', '', '{', '', '', '', '', '', 'p', 'r', 'i', 'n', 't', 'f', '(', '"', 'H', 'e', 'l', 'l', 'o', '', 'W', 'o', 'r', 'l', 'd', '!', '"', ')', ';', '', '', '', '', '', 'r', 'e', 't', 'u', 'r', 'n', '', '0', ';', '', '}']
'''

f = open(f"testing_simple_c_programs/hello_world.c", "r")
Program = f.read()

print(Program)

'''
Output:
int main()
{
    printf("Hello World!");
    return 0;
}
'''

def SpaceRemover(Program):
    scanned_program = []
    for line in Program:
        if (line.strip() != ''):
            scanned_program.append(line.strip())
    print(scanned_program)
    return scanned_program
    
'''
['i', 'n', 't', 'm', 'a', 'i', 'n', '(', ')', '{', 'p', 'r', 'i', 'n', 't', 'f', '(', '"', 'H', 'e', 'l', 'l', 'o', 'W', 'o', 'r', 'l', 'd', '!', '"', ')', ';', 'r', 'e', 't', 'u', 'r', 'n', '0', ';', '}']
'''