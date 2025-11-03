int main() {
  int a, b, c, d;
  b = 42;
  a = b;      // a -> b
  c = a;      // c -> b
  d = c;      // d -> b
  return d;   // should return 42
}
