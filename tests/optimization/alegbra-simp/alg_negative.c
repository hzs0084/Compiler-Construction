int main() {
  int x, y;
  x = 5;
  y = 0 - x;     // DO NOT simplify to x or -x incorrectly
  return y;      // must be -5
}
