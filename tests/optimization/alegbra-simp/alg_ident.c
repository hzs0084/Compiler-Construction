int main() {
  int x, a,b,c,d,e,f,g,h;
  x = 7;
  a = x + 0;   // -> x
  b = 0 + x;   // -> x
  c = x - 0;   // -> x
  d = x * 1;   // -> x
  e = 1 * x;   // -> x
  f = x * 0;   // -> 0
  g = 0 * x;   // -> 0
  h = x / 1;   // -> x
  // sum:  (x+x+x+x+x) + (0+0) + x  = 6*x = 42
  return a + b + c + d + e + f + g + h;
}
