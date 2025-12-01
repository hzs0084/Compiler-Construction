// div_runtime.c
int main() {
  int a; int b; int q; int i;
  a = 0; b = 3; i = 0;
  while (i < 5) { a = a - i; i = i + 1; } // a now depends on loop
  q = a / b;
  return q;
}
