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
