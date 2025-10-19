int main() {
  { int z; }
  z = 3;        // error: undeclared 'z' (out of scope)
  return 0;
}
