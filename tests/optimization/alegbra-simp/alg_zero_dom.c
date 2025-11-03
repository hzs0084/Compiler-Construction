int main() {
  int x, y, z;
  x = 9;
  y = x * 0;     // -> 0 (algebra)
  z = y + x*1;   // z = 0 + x -> x
  return z;      // -> 9
}
