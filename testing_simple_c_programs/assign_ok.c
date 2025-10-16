int main() {
  a = 5;
  b = a = 2 + 3;
  c = (a = 1) + (b = 2);
  return c;
}
