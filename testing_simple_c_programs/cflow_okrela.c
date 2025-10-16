int main() {
    int x, y;
    x = 0;
    y = 2;
    if (x < y) {
      x = x + 1;
    } else {
      x = x - 1;
    }
    while (x < 5 && y == 2) {
      x = x + 1;
    }
    return x;
  }
  