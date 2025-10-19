int main() {
  int x;
  { int z; }
  return x;
}
// Expected
// nameOfVariables: x
// typeOfVariables: int