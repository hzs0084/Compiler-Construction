int main() {
  int x, y;
  x = 4;
  y = x + 2;  // not folded yet (needs propagation)
  return y;
}
