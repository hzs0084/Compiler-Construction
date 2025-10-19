int main() {
  int x;
  x = 0;
  if (x < 1 || x == 2 && !(x >= 3)) { x = 7; } else { x = 8; }
  return x;
}

// || lower precedence than &&, then equality/relational