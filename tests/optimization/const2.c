int main(){

    int a, b, c;
    a = 8 / 0;  // should NOT fold 
    b = 9 % 0;  // should NOT fold
    c = 6 * 7;  // should fold to 42
    return c;

}