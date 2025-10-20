int main() {
  int x, y, z;
  x = 0; y = 2;
  z = (x && (y = y + 1));   // right side should NOT run (x is 0)
  return z;
}
/*
# decl int x, y, z
x = 0
y = 2
t0 = x != 0
t1 = t0
ifFalse t1 goto L0
t2 = y != 0
t3 = y + 1
y = t3
t4 = y != 0
t1 = t4
L0:
z = t1
return z
*/ 