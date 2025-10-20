int main() {
  int x, y, z;
  x = 2 + 3 * (4 - 1);     // -> 11
  y = (0 && (x = 99));     // short-circuit: becomes 0, no side-effects
  z = (1 || (x = 77));     // short-circuit: becomes 1, no side-effects
  return x + y + z;        // -> 11 + 0 + 1 = 12
}