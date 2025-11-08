int main() {
  int s;
  s = 5;
  while (0) {
    s = s + 1; // never executes
  }
  return s;
}
