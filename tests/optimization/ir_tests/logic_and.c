int main() {
  if ((3-3) && 100) {  // 0 && 100 => false
    return 111;
  } else {
    return 222;
  }
}

//Should just return 222