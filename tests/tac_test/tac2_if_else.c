int main() {
  int x;
  x = 0;
  if (x < 1) { x = x + 1; } else { x = x - 1; }
  return x;
}


/*
# function main (int)
# decl int x
x = 0
t0 = x < 1
ifFalse t0 goto L0
t1 = x + 1
x = t1
goto L1
L0:
t2 = x - 1
x = t2
L1:
return x
*/