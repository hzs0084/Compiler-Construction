int main() {
  int x, y;
  x = 2 + 2;    // 4
  if (x == 4) {
    y = x * 5;  // 20
    x = 0;      // overwrites x; prior x is now dead
  } else {
    y = 3;      // unreachable
  }
  return y;     // expect 20
}