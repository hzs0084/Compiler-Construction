int main() {
  int x, y, z;
  y = 2;
  x = y;      // x -> y (i.e., x == 2)
  y = 7;      // kill aliases that point to y
  z = x + 1;  // MUST use old x==2, not new y==7 -> z == 3
  return z;
}
