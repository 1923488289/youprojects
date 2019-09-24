def fun(n):
    a,b=0,1
    i=0
    while i<n:
        yield b
        a,b=b,a+b
        i +=1

for x in fun(10):
    print(x)
