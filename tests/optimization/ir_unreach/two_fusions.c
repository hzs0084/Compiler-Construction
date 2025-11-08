int main() {
  int x, y;
  x = 3 + 3;       // 6
  if (x == 6) {
    y = x + 1;     // 7
  } else {
    y = 999;       // unreachable
  }
  return y;
}
