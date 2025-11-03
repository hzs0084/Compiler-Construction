int main() {
  int x, y, z;
  x = 5;
  y = x;        // y -> x
  z = y + 1;    // should become z = x + 1 then z = 6
  return z;
}
