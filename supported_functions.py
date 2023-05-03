def mult(a, b):
    c=0
    while (b>0):
        c+=a
        b-=1
    return c

def random():
    c = 10
    e = 102
    b = 123123
    d = 1232
    f = 10
    while (c < 900):
        c+=1
    return c

def modulus(x, mod):
    new_x = x
    while (x >= mod):
        x -= mod
    return x

def multiply(a, b):
    val = 0
    while (b > 0):
        val += a
        b -= 1
    return val

def factorial(n):
    val = 1
    x = 2
    while (x <= n):
        val = multiply(val, x)
        x += 1
    return val

def add(a,b):
    val = 0
    val += a
    val += b
    return val

def sub(a,b):
    val = 0
    val += a
    val -= b
    return val