int main() {
  int a, b, c, d, e;
  a = 2 + 3;
  b = - 5;
  c = 10 / 2;
  d = 1 && 0;    // your lowering likely turns this into compares + branches
  e = 3 < 5;
  return a + b + c + d + e;
}
