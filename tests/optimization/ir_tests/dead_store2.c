int main() {
  int x, y;
  x = 7;
  y = x;
  x = 0;      // overwrites x
  return y + y;  // should fold to 14 because old x doesn’t matter
}