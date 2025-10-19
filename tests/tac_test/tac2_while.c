int main() {
  int x;
  x = 0;
  while (x < 3) { x = x + 1; }
  return x;
}
/*
# function main (int)
# decl int x
x = 0
L0:
t0 = x < 3
ifFalse t0 goto L1
t1 = x + 1
x = t1
goto L0
L1:
return x
*/