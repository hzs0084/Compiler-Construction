int main() {
  int x, y, u, v;
  x = 4;
  y = x;         // y -> x
  u = y + 0;     // -> x
  v = 1 * u;     // -> x
  return v;      // -> 4
}
