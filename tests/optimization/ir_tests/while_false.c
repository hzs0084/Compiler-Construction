int main() {
  int s;
  s = 5;
  while (0) {   // body unreachable
    s = s + 1;
  }
  return s;     // 5
}
//  Should just return 5