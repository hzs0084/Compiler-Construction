int main() {
  a = 5;
  b = a = 2 + 3;
  c = (a = 1) + (b = 2);
  return c;
}


// there should be an error here in the future because the type is not defined
// would fall under semantics


