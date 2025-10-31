int main() {
  int x;
  x = 1;
  while (x < 3) {   // not a compile-time constant
    x = x + 1;
  }
  return x;   // 3
}
// Should just return 3