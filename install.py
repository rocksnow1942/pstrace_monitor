import pip 

__all = [
"Pillow == 7.1.2",
"compress_pickle == 1.1.1",
"matplotlib == 3.1.3",
"numpy == 1.18.1",
"pyserial == 3.4",
"requests == 2.23.0",
"scipy == 1.4.1",
"watchdog == 0.10.2",
"websocket_client==0.57.0",
"scikit-learn==0.23.2"
]

windows = ["pywin32 == 228","win32compat == 221.26",]
linux = []
darwin = []

def install(pkg):
    for p in pkg:
        pip.main(['install',p])


if __name__ == "__main__":
    from sys import platform 
    install(__all) 
    if platform == 'darwin':
        install(darwin)
    if platform == 'win32':
        install(windows)
    if platform.startswith('linux'):
        install(linux)