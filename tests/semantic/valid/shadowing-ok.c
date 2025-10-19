int main() {
  int x;
  { int x; x = 1; }  // inner x shadows outer x
  return 0;
}
