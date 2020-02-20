from cffi import FFI
import subprocess
# try:
#     subprocess.check_call(["make", "-j4"], cwd="/data/openpilot/selfdrive/traffic")
# except:
#     pass
# try:
#     subprocess.check_call(["scons", "-u"], cwd="/data/openpilot/selfdrive/traffic")
# except:
#     pass


def get_wrapper():
    libmpc_fn = "/data/openpilot/selfdrive/traffic/libtraffic.so"

    ffi = FFI()
    ffi.cdef("""    
    void predictTraffic(int inputArray[1257630], float* outputArray);
    int runModelLoop();
    """)

    return ffi.dlopen(libmpc_fn), ffi
