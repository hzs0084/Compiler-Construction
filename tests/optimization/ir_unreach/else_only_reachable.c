int main() {
  int x;
  if (0) {
    x = 1;      // unreachable
  } else {
    x = 2;      // reachable
  }
  return x;
}
