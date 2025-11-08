int main() {
  int x, y;
  x = 2 + 2;         // 4
  if (x == 4) {
    y = 1;
  } else {
    y = 2;           // unreachable
  }
  return y;
}
