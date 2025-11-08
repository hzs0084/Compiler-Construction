int main() {
  int z;
  if (1) {
    if (0) {
      z = 1;      // unreachable
    } else {
      z = 2;      // reachable
    }
  } else {
    z = 3;        // unreachable
  }
  return z;
}
