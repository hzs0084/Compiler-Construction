int main() {
  int x, y, z, w;
  x = 7;
  y = x + 0;   // -> y = x
  z = 0 + x;   // -> z = x
  w = x * 1;   // -> w = x
  x = x * 0;   // -> x = 0
  z = z / 1;   // -> z = z
  return y + z + w + x;
}
