import time


def timing(f, prefix=""):
    def wrap(*args, **kwargs):
        time1 = time.time()
        ret = f(*args, **kwargs)
        time2 = time.time()
        print('{:s} {:s} function took {:.3f} ms'.format(
            prefix, f.__name__, (time2-time1)*1000.0))
        return ret
    return wrap


def my_func(a, b='i_am_b'):
    time.sleep(1)
    return (a, b)


if __name__ == '__main__':
    val = timing(my_func)(9001)
    print('returned from my_func :: ' + str(val))
